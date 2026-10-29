#!/usr/bin/env python3
"""GPU-host gateway for source-pinned LOUKSNAPG model execution.

Run one process per domain on a trusted GPU host behind an HTTPS reverse proxy.
It downloads only the immutable repository revision defined by the shipped policy,
verifies source configuration/index and model shard identities, then signs its
identity and task responses with a per-domain HMAC key. This script must not run
on the constrained LOUKSNA PC.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path(__file__).resolve().parents[1] / "cajita-luna-runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from cajita_remote_execution import (
    IDENTITY_SCHEMA, POLICY_SCHEMA, RESPONSE_SCHEMA, REQUEST_SCHEMA, SIGNED_IDENTITY_SCHEMA,
    RemoteExecutionError, canonical_json, load_policy, sha256_bytes, utc_now,
)

GATEWAY_VERSION = "1.0.0"
MAX_AUDIO_BYTES = 32 * 1024 * 1024
MAX_AUDIO_SECONDS = 60
MAX_REQUEST_BYTES = 48 * 1024 * 1024
MAX_NEW_TOKENS = 256
REPLAY_WINDOW_SECONDS = 300
NONCE_CAPACITY = 10000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hmac_hex(key: bytes, payload: dict) -> str:
    return hmac.new(key, canonical_json(payload), hashlib.sha256).hexdigest()


def _key_from_environment() -> bytes:
    value = os.environ.get("LOUKSNAPG_GATEWAY_KEY_HEX", "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise RuntimeError("GATEWAY_HMAC_KEY_MISSING_OR_INVALID")
    key = bytes.fromhex(value)
    if len(key) != 32:
        raise RuntimeError("GATEWAY_HMAC_KEY_LENGTH_INVALID")
    return key


def source_identity(domain_id: str, spec: dict, model_root: Path, *,
                    gateway_code_sha256: str, gateway_commit: str) -> dict:
    root = Path(model_root).resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("MODEL_ROOT_MISSING_OR_UNSAFE")
    config = root / "config.json"
    if config.is_symlink() or not config.is_file():
        raise RuntimeError("SOURCE_CONFIG_MISSING")
    config_sha = sha256_file(config)
    if config_sha != spec["source_config_sha256"]:
        raise RuntimeError("SOURCE_CONFIG_SHA256_MISMATCH")
    index_sha = None
    if spec.get("source_index_sha256") is not None:
        index = root / "model.safetensors.index.json"
        if index.is_symlink() or not index.is_file():
            raise RuntimeError("SOURCE_WEIGHT_INDEX_MISSING")
        index_sha = sha256_file(index)
        if index_sha != spec["source_index_sha256"]:
            raise RuntimeError("SOURCE_WEIGHT_INDEX_SHA256_MISMATCH")
    expected = {row["path"]: row for row in spec["weight_files"]}
    actual_names = sorted(
        path.name for path in root.iterdir()
        if path.is_file() and not path.is_symlink()
        and (path.name.endswith(".safetensors") or path.name == "model.safetensors")
    )
    if set(actual_names) != set(expected):
        raise RuntimeError("SOURCE_WEIGHT_FILE_SET_MISMATCH")
    weight_files = []
    for name in actual_names:
        path = root / name
        wanted = expected[name]
        size = path.stat().st_size
        if wanted.get("bytes") is not None and size != wanted["bytes"]:
            raise RuntimeError("SOURCE_WEIGHT_SIZE_MISMATCH:" + name)
        digest = sha256_file(path)
        if wanted.get("sha256") is not None and not hmac.compare_digest(digest, wanted["sha256"]):
            raise RuntimeError("SOURCE_WEIGHT_SHA256_MISMATCH:" + name)
        weight_files.append({"path": name, "bytes": size, "sha256": digest})
    weight_files.sort(key=lambda row: row["path"].encode("utf-8"))
    inventory_sha = sha256_bytes(canonical_json(weight_files))
    return {
        "schema": IDENTITY_SCHEMA,
        "domain_id": domain_id,
        "model_id": spec["model_id"],
        "source_repo": spec["source_repo"],
        "source_revision": spec["source_revision"],
        "source_config_sha256": config_sha,
        "source_index_sha256": index_sha,
        "weight_files": weight_files,
        "weight_inventory_sha256": inventory_sha,
        "model_loaded": True,
        "gateway_version": GATEWAY_VERSION,
        "gateway_code_sha256": gateway_code_sha256,
        "gateway_source_commit": gateway_commit or "UNRECORDED",
        "created_at_utc": utc_now(),
    }


class ModelWorker:
    def __init__(self, domain_id: str, spec: dict, model_root: Path, identity: dict):
        import torch
        self.torch = torch
        self.domain_id = domain_id
        self.spec = spec
        self.model_root = Path(model_root).resolve(strict=True)
        self.identity = identity
        torch.set_num_threads(1)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass
        model_id = spec["model_id"]
        if domain_id in ("D01_CEREBRO", "D06_SISTEMA_INTELIGENTE"):
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.processor = None
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_root), local_files_only=True, trust_remote_code=False
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                str(self.model_root), local_files_only=True, trust_remote_code=False,
                device_map="auto", torch_dtype="auto", low_cpu_mem_usage=True,
            )
        elif domain_id == "D04_TRADUCTOR_INTELIGENTE":
            from transformers import AutoProcessor, SeamlessM4Tv2Model
            self.processor = AutoProcessor.from_pretrained(
                str(self.model_root), local_files_only=True, trust_remote_code=False
            )
            self.tokenizer = None
            self.model = SeamlessM4Tv2Model.from_pretrained(
                str(self.model_root), local_files_only=True, trust_remote_code=False,
                device_map="auto", torch_dtype="auto", low_cpu_mem_usage=True,
            )
        elif domain_id == "D03_TRANSCRIPCION":
            from transformers import WhisperForConditionalGeneration, WhisperProcessor
            self.processor = WhisperProcessor.from_pretrained(
                str(self.model_root), local_files_only=True
            )
            self.tokenizer = None
            self.model = WhisperForConditionalGeneration.from_pretrained(
                str(self.model_root), local_files_only=True, use_safetensors=True,
                device_map="auto", torch_dtype="auto", low_cpu_mem_usage=True,
            )
            self.generation_config = self.model.generation_config
        else:
            raise RuntimeError("GATEWAY_DOMAIN_NOT_IMPLEMENTED:" + domain_id)
        self.model.eval()
        self.input_device = self.model.get_input_embeddings().weight.device
        if str(self.input_device) == "meta":
            raise RuntimeError("MODEL_INPUT_DEVICE_UNMATERIALIZED")
        # Ensure the worker did not accidentally load a different model family.
        if getattr(getattr(self.model, "config", None), "_name_or_path", model_id) not in (None, "", model_id, str(self.model_root)):
            raise RuntimeError("LOADED_MODEL_IDENTITY_UNEXPECTED")

    def _move(self, batch):
        if hasattr(batch, "to"):
            return batch.to(self.input_device)
        return {key: value.to(self.input_device) if hasattr(value, "to") else value for key, value in batch.items()}

    def infer(self, request: dict) -> tuple[str, int]:
        operation = request.get("operation")
        domain = request.get("domain_id")
        data = request.get("input")
        limits = request.get("limits")
        if not isinstance(data, dict) or not isinstance(limits, dict):
            raise ValueError("TASK_INPUT_OR_LIMITS_INVALID")
        tokens = limits.get("max_new_tokens")
        if isinstance(tokens, bool) or not isinstance(tokens, int) or not 1 <= tokens <= MAX_NEW_TOKENS:
            raise ValueError("TASK_TOKEN_LIMIT_INVALID")
        torch = self.torch
        with torch.inference_mode():
            if domain in ("D01_CEREBRO", "D06_SISTEMA_INTELIGENTE") and operation in ("generate_text", "analyze_reasoning"):
                prompt = data.get("prompt")
                if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 16384:
                    raise ValueError("PROMPT_INVALID")
                messages = [{"role": "user", "content": prompt}]
                if getattr(self.tokenizer, "chat_template", None):
                    encoded = self.tokenizer.apply_chat_template(
                        messages, add_generation_prompt=True, tokenize=True,
                        return_dict=True, return_tensors="pt",
                    )
                else:
                    encoded = self.tokenizer(prompt, return_tensors="pt")
                encoded = self._move(encoded)
                generated = self.model.generate(
                    **encoded, max_new_tokens=tokens, do_sample=False,
                    use_cache=True, pad_token_id=self.tokenizer.eos_token_id,
                )
                input_len = int(encoded["input_ids"].shape[-1])
                new_ids = generated[0, input_len:]
                answer = self.tokenizer.decode(new_ids, skip_special_tokens=True).strip()
                count = int(new_ids.shape[-1])
            elif domain == "D04_TRADUCTOR_INTELIGENTE" and operation == "translate_text":
                text = data.get("text")
                src = data.get("src_lang")
                tgt = data.get("tgt_lang")
                if not isinstance(text, str) or not text.strip() or len(text) > 16384:
                    raise ValueError("TRANSLATION_TEXT_INVALID")
                if not isinstance(src, str) or not isinstance(tgt, str) or src == tgt:
                    raise ValueError("TRANSLATION_LANGUAGE_INVALID")
                encoded = self.processor(text=text, src_lang=src, return_tensors="pt")
                encoded = self._move(encoded)
                generated = self.model.generate(
                    **encoded, tgt_lang=tgt, generate_speech=False, max_new_tokens=tokens,
                )
                sequences = getattr(generated, "sequences", generated)
                decoded = self.processor.batch_decode(sequences, skip_special_tokens=True)
                answer = str(decoded[0]).strip() if decoded else ""
                count = int(sequences.shape[-1]) if hasattr(sequences, "shape") else len(answer.split())
            elif domain == "D03_TRANSCRIPCION" and operation == "transcribe_audio":
                import numpy as np
                import soundfile as sf
                from scipy.signal import resample_poly
                import math
                audio_b64 = data.get("audio_base64")
                audio_sha = data.get("audio_sha256")
                if not isinstance(audio_b64, str) or not isinstance(audio_sha, str):
                    raise ValueError("AUDIO_PAYLOAD_MISSING")
                try:
                    raw = base64.b64decode(audio_b64, validate=True)
                except Exception as exc:
                    raise ValueError("AUDIO_BASE64_INVALID") from exc
                if not 1 <= len(raw) <= MAX_AUDIO_BYTES or not hmac.compare_digest(sha256_bytes(raw), audio_sha):
                    raise ValueError("AUDIO_SIZE_OR_HASH_MISMATCH")
                audio, rate = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
                if audio.ndim == 2:
                    audio = audio.mean(axis=1, dtype=np.float32)
                if audio.ndim != 1 or not len(audio) or not np.isfinite(audio).all():
                    raise ValueError("AUDIO_WAVEFORM_INVALID")
                if len(audio) / float(rate) > MAX_AUDIO_SECONDS:
                    raise ValueError("AUDIO_DURATION_LIMIT_EXCEEDED")
                if rate != 16000:
                    divisor = math.gcd(int(rate), 16000)
                    audio = resample_poly(audio, 16000 // divisor, int(rate) // divisor).astype(np.float32, copy=False)
                encoded = self.processor(audio, sampling_rate=16000, return_tensors="pt")
                encoded["input_features"] = encoded["input_features"].to(dtype=torch.float32, device=self.input_device)
                generated = self.model.generate(
                    **encoded, max_new_tokens=tokens, do_sample=False,
                    language="en", task="transcribe", repetition_penalty=1.08,
                    no_repeat_ngram_size=3, renormalize_logits=True,
                )
                decoded = self.processor.batch_decode(generated, skip_special_tokens=True)
                answer = str(decoded[0]).strip() if decoded else ""
                count = int(generated.shape[-1])
            else:
                raise ValueError("DOMAIN_OPERATION_NOT_REGISTERED")
        if not answer or count < 1:
            raise ValueError("MODEL_OUTPUT_EMPTY")
        return answer[:16384], min(count, tokens)


class GatewayHTTPServer(HTTPServer):
    def __init__(self, address, handler, *, key: bytes, key_id: str,
                 domain_id: str, spec: dict, identity: dict, worker: ModelWorker):
        super().__init__(address, handler)
        self.key = key
        self.key_id = key_id
        self.domain_id = domain_id
        self.spec = spec
        self.identity = identity
        self.identity_sha256 = sha256_bytes(canonical_json(identity))
        self.worker = worker
        self.seen_nonces = OrderedDict()


class Handler(BaseHTTPRequestHandler):
    server: GatewayHTTPServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        # Never log prompts, transcribed audio, tokens, request bodies or signatures.
        sys.stderr.write("louksnapg-gateway " + format % args + "\n")

    def _send(self, code: int, value: dict):
        raw = canonical_json(value)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def _signed(self, payload: dict) -> dict:
        result = dict(payload)
        result["signature"] = _hmac_hex(self.server.key, payload)
        return result

    def do_GET(self):
        if self.path != "/v1/identity":
            self._send(404, {"status": "FAIL_CLOSED", "error": "ENDPOINT_NOT_FOUND"})
            return
        payload = {
            "schema": SIGNED_IDENTITY_SCHEMA,
            "key_id": self.server.key_id,
            "identity": self.server.identity,
            "issued_at_utc": utc_now(),
        }
        self._send(200, self._signed(payload))

    def do_POST(self):
        if self.path != "/v1/infer":
            self._send(404, {"status": "FAIL_CLOSED", "error": "ENDPOINT_NOT_FOUND"})
            return
        try:
            raw_len = self.headers.get("Content-Length", "")
            if not raw_len.isdigit() or not 1 <= int(raw_len) <= MAX_REQUEST_BYTES:
                raise ValueError("REQUEST_SIZE_INVALID")
            raw = self.rfile.read(int(raw_len))
            if len(raw) != int(raw_len):
                raise ValueError("REQUEST_TRUNCATED")
            try:
                request = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("REQUEST_JSON_INVALID") from exc
            if not isinstance(request, dict) or canonical_json(request) != raw:
                raise ValueError("REQUEST_NOT_CANONICAL_JSON")
            if self.headers.get("X-Louksnapg-Key-Id") != self.server.key_id:
                raise ValueError("REQUEST_KEY_ID_MISMATCH")
            supplied = self.headers.get("X-Louksnapg-Request-Signature", "")
            expected = hmac.new(self.server.key, raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(supplied, expected):
                raise ValueError("REQUEST_SIGNATURE_INVALID")
            if request.get("schema") != REQUEST_SCHEMA or request.get("key_id") != self.server.key_id:
                raise ValueError("REQUEST_SCHEMA_OR_KEY_ID_MISMATCH")
            if request.get("domain_id") != self.server.domain_id:
                raise ValueError("REQUEST_DOMAIN_MISMATCH")
            if request.get("model_id") != self.server.spec["model_id"] or request.get("source_revision") != self.server.spec["source_revision"]:
                raise ValueError("REQUEST_SOURCE_IDENTITY_MISMATCH")
            if request.get("identity_sha256") != self.server.identity_sha256:
                raise ValueError("REQUEST_IDENTITY_DIGEST_MISMATCH")
            issued = datetime.fromisoformat(str(request.get("issued_at_utc", "")).replace("Z", "+00:00"))
            if issued.tzinfo is None or abs(time.time() - issued.timestamp()) > 120:
                raise ValueError("REQUEST_TIMESTAMP_EXPIRED")
            nonce = request.get("nonce")
            if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{48}", nonce):
                raise ValueError("REQUEST_NONCE_INVALID")
            now = time.time()
            for old in list(self.server.seen_nonces):
                if now - self.server.seen_nonces[old] > REPLAY_WINDOW_SECONDS:
                    del self.server.seen_nonces[old]
                else:
                    break
            if nonce in self.server.seen_nonces:
                raise ValueError("REQUEST_REPLAY_DETECTED")
            if len(self.server.seen_nonces) >= NONCE_CAPACITY:
                raise ValueError("REQUEST_REPLAY_CACHE_FULL")
            self.server.seen_nonces[nonce] = now
            answer, token_count = self.server.worker.infer(request)
            response_payload = {
                "schema": RESPONSE_SCHEMA,
                "request_id": request["request_id"],
                "request_sha256": sha256_bytes(canonical_json(request)),
                "identity_sha256": self.server.identity_sha256,
                "domain_id": self.server.domain_id,
                "model_id": self.server.spec["model_id"],
                "source_revision": self.server.spec["source_revision"],
                "status": "PASS_REMOTE_EXECUTION",
                "output_text": answer,
                "generated_token_count": token_count,
                "issued_at_utc": utc_now(),
            }
            self._send(200, self._signed(response_payload))
        except Exception as exc:
            # Error responses do not expose exception text, user input or secrets.
            error = str(exc) if isinstance(exc, ValueError) else "GATEWAY_TASK_FAILED"
            self._send(422, {"schema": "LOUKSNAPG_GATEWAY_ERROR/1.0", "status": "FAIL_CLOSED", "error": error[:120]})


def _validate_gpu_preflight(allow_cpu: bool):
    import torch
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    if not torch.cuda.is_available() and not allow_cpu:
        raise RuntimeError("REMOTE_GATEWAY_GPU_REQUIRED; no model download or local inference started")
    return "CUDA" if torch.cuda.is_available() else "CPU_EXPLICITLY_ALLOWED"


def _materialize_source(spec: dict, cache_root: Path) -> Path:
    from huggingface_hub import snapshot_download
    path = cache_root / spec["model_id"].replace("/", "--") / spec["source_revision"]
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=spec["source_repo"],
        revision=spec["source_revision"],
        local_dir=str(path),
        token=os.environ.get("HF_TOKEN") or None,
        max_workers=1,
        allow_patterns=[
            "config.json", "generation_config.json", "model.safetensors.index.json",
            "model-*.safetensors", "model.safetensors", "tokenizer*", "vocab.json",
            "merges.txt", "special_tokens_map.json", "added_tokens.json",
            "preprocessor_config.json", "processor_config.json", "sentencepiece.bpe.model",
            "spm_char_lang38_tc.model", "normalizer.json", "chat_template.jinja", "*.jinja",
        ],
    )
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-id", choices=(
        "D01_CEREBRO", "D03_TRANSCRIPCION", "D04_TRADUCTOR_INTELIGENTE", "D06_SISTEMA_INTELIGENTE"
    ), required=True)
    parser.add_argument("--policy", type=Path, default=RUNTIME_DIR / "CAJITA_REMOTE_MODEL_POLICY.json")
    parser.add_argument("--cache-dir", type=Path, default=Path(os.environ.get("LOUKSNAPG_GATEWAY_CACHE", "/var/lib/louksnapg/models")))
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--allow-cpu", action="store_true", help="Only for deliberate remote testing; never use on the constrained LOUKSNA PC.")
    parser.add_argument("--self-test", action="store_true", help="Validate the policy only; downloads no model and performs no inference.")
    args = parser.parse_args(argv)

    policy = load_policy(args.policy.parent) if args.policy.name == "CAJITA_REMOTE_MODEL_POLICY.json" else None
    if args.policy.name != "CAJITA_REMOTE_MODEL_POLICY.json":
        try:
            value = json.loads(args.policy.read_text(encoding="utf-8"))
            if value.get("schema") != POLICY_SCHEMA:
                raise RuntimeError("REMOTE_MODEL_POLICY_SCHEMA_MISMATCH")
            policy = value
        except Exception as exc:
            raise SystemExit("FAIL_CLOSED:" + type(exc).__name__)
    if args.domain_id not in policy.get("domains", {}):
        raise SystemExit("FAIL_CLOSED:REMOTE_DOMAIN_NOT_REGISTERED")
    spec = policy["domains"][args.domain_id]
    if args.self_test:
        if not re.fullmatch(r"[0-9a-f]{40}", spec["source_revision"]):
            raise SystemExit("FAIL_CLOSED:SOURCE_REVISION_NOT_IMMUTABLE")
        print(json.dumps({
            "status": "PASS_POLICY_ONLY_NOT_MODEL_EXECUTION",
            "domain_id": args.domain_id,
            "model_id": spec["model_id"],
            "source_revision": spec["source_revision"],
            "source_config_sha256": spec["source_config_sha256"],
            "source_index_sha256": spec.get("source_index_sha256"),
            "local_model_downloaded": False,
            "inference_executed": False,
            "certification": "NOT_GRANTED",
        }, sort_keys=True))
        return 0

    key = _key_from_environment()
    key_id = os.environ.get("LOUKSNAPG_GATEWAY_KEY_ID", "")
    if key_id != spec["key_id"]:
        raise SystemExit("FAIL_CLOSED:GATEWAY_KEY_ID_MISMATCH")
    code_commit = os.environ.get("LOUKSNAPG_GATEWAY_SOURCE_COMMIT", "")
    if not re.fullmatch(r"[0-9a-f]{40}", code_commit):
        raise SystemExit("FAIL_CLOSED:GATEWAY_SOURCE_COMMIT_REQUIRED")
    allow_cpu = args.allow_cpu and os.environ.get("LOUKSNAPG_GATEWAY_ALLOW_CPU") == "1"
    try:
        accelerator = _validate_gpu_preflight(allow_cpu)
        model_root = _materialize_source(spec, args.cache_dir)
        script_sha = sha256_file(Path(__file__).resolve())
        identity = source_identity(
            args.domain_id, spec, model_root,
            gateway_code_sha256=script_sha, gateway_commit=code_commit,
        )
        worker = ModelWorker(args.domain_id, spec, model_root, identity)
    except Exception as exc:
        raise SystemExit("FAIL_CLOSED:" + type(exc).__name__ + ":" + str(exc)[:240])

    server = GatewayHTTPServer(
        (args.bind, args.port), Handler, key=key, key_id=key_id,
        domain_id=args.domain_id, spec=spec, identity=identity, worker=worker,
    )
    print(json.dumps({
        "status": "REMOTE_GATEWAY_READY",
        "domain_id": args.domain_id,
        "model_id": spec["model_id"],
        "source_revision": spec["source_revision"],
        "weight_inventory_sha256": identity["weight_inventory_sha256"],
        "gateway_code_sha256": identity["gateway_code_sha256"],
        "accelerator": accelerator,
        "bind": args.bind,
        "port": args.port,
        "transport_requirement": "HTTPS_REVERSE_PROXY_REQUIRED_FOR_NON_LOOPBACK_ACCESS",
        "certification": "NOT_GRANTED",
    }, sort_keys=True), flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
