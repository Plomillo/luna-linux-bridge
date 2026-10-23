#!/usr/bin/env python3
"""Process-isolated functional adapters and resource evidence for Cajita's six domains.

Model stages run one per child process. The supervisor samples worker RSS, enforces a
worker-memory ceiling, hashes packaged weights, and verifies that each worker is reaped.
Raw request text is never persisted to the audit or measurement report.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gc
import hashlib
import importlib.util
import json
import os
import pathlib
import platform
import re
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import wave
from typing import Any

try:
    import resource
except ImportError:  # pragma: no cover - non-POSIX hosts fail closed for resource evidence
    resource = None

ROOT = pathlib.Path(__file__).resolve().parent
SCHEMA = "CAJITA_MODEL_ADAPTERS/1.0"
MAX_GLOBAL_RAM_MIB = 1024
DEFAULT_WORKER_RSS_LIMIT_MIB = 850
MAX_PARENT_PLUS_WORKER_RSS_MIB = 900
DEFAULT_STAGE_TIMEOUT_SECONDS = 600
MAX_INPUT_FILE_BYTES = 50 * 1024 * 1024
MODEL_MANIFEST = ROOT / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
MANIFEST_SHA256 = "50ae6f9cf60ef84d4be15d35af998c5ad64685f54b882cc3fff8e812357e3483"

DOMAINS: dict[str, dict[str, Any]] = {
    "D01_CEREBRO": {
        "name": "Cerebro",
        "kind": "local-model",
        "module": ROOT / "1. Cerebro" / "cerebro_180mb_runtime.py",
        "asset": "1. Cerebro/model.safetensors",
        "capability": "answer_generation",
    },
    "D02_ORQUESTACION": {
        "name": "Orquestación",
        "kind": "control-plane",
        "module": ROOT / "2. Orquestación" / "Orquestador" / "CLIs" / "cli_registry.py",
        "asset": None,
        "capability": "job_orchestration",
    },
    "D03_TRANSCRIPCION": {
        "name": "Transcripción",
        "kind": "local-model",
        "module": ROOT / "3. Transcripción" / "lowrank_runtime.py",
        "asset": "3. Transcripción/model.safetensors",
        "capability": "audio_transcription",
    },
    "D04_TRADUCTOR_INTELIGENTE": {
        "name": "Traductor inteligente",
        "kind": "local-model",
        "module": ROOT / "4. Traductor Inteligente" / "Traducción general" / "lowrank_runtime.py",
        "asset": "4. Traductor Inteligente/Traducción general/model.safetensors",
        "capability": "text_translation",
    },
    "D05_INTELIGENCIA_DOCUMENTAL": {
        "name": "Inteligencia documental",
        "kind": "local-model-plus-pdf-output",
        "module": ROOT / "5. Inteligencia documental" / "INTELDOC_GLOBAL_30MB_CANDIDATE_V9" / "docling" / "compact_upstream_hf_candidate" / "docling_30mb_runtime_v1.py",
        "asset": "5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_weights.bin",
        "capability": "document_extraction",
    },
    "D06_SISTEMA_INTELIGENTE": {
        "name": "Sistema inteligente / razonamiento",
        "kind": "local-model",
        "module": ROOT / "6. Sistema Inteligente" / "Análisis Avanzado" / "lowrank_runtime_v2.py",
        "asset": "6. Sistema Inteligente/Análisis Avanzado/model.safetensors",
        "capability": "advanced_reasoning",
    },
}

TASK_ADAPTER_STATUS = {
    "answer_generation": "REGISTERED_CANDIDATE",
    "job_orchestration": "REGISTERED_DIAGNOSTIC_ONLY",
    "audio_transcription": "REGISTERED_CANDIDATE",
    "text_translation": "REGISTERED_CANDIDATE",
    "document_extraction": "REGISTERED_CANDIDATE",
    "pdf_generation": "REGISTERED_STANDARD_LIBRARY",
    "advanced_reasoning": "REGISTERED_CANDIDATE",
    # An ONNX payload exists, but the current lock does not contain onnxruntime and the
    # architecture/adapter is unverified; do not claim anti-hallucination inference.
    "anti_hallucination_onnx": "BLOCKED_RUNTIME_AND_ARCHITECTURE_UNVERIFIED",
}

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def current_rss_mib(pid: int | None = None) -> float | None:
    if not sys.platform.startswith("linux"):
        return None
    status = pathlib.Path(f"/proc/{pid or os.getpid()}/status")
    try:
        for line in status.read_text(encoding="ascii").splitlines():
            if line.startswith("VmRSS:"):
                return round(int(line.split()[1]) / 1024, 3)
    except (OSError, ValueError, IndexError):
        return None
    return None

def peak_rss_mib() -> float | None:
    if resource is None:
        return None
    try:
        # Linux reports ru_maxrss in KiB.
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(float(value) / 1024, 3) if value else None
    except (ValueError, OSError):
        return None

def set_single_cpu_affinity() -> dict[str, Any]:
    report: dict[str, Any] = {"thread_budget": 1, "affinity_applied": False}
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    if hasattr(os, "sched_getaffinity") and hasattr(os, "sched_setaffinity"):
        try:
            allowed = sorted(os.sched_getaffinity(0))
            if allowed:
                os.sched_setaffinity(0, {allowed[0]})
                report.update({"affinity_applied": True, "cpu_id": allowed[0]})
        except OSError as exc:
            report["affinity_error"] = type(exc).__name__
    return report

def load_module(path: pathlib.Path, module_name: str):
    path = path.resolve(strict=True)
    if not path.is_file():
        raise FileNotFoundError("DOMAIN_ADAPTER_MODULE_MISSING")
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("DOMAIN_ADAPTER_IMPORT_SPEC_INVALID")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def expected_asset(asset_rel: str) -> dict[str, Any]:
    if not MODEL_MANIFEST.is_file():
        raise RuntimeError("WEIGHTS_MANIFEST_MISSING")
    manifest = json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))
    if sha256_file(MODEL_MANIFEST) != MANIFEST_SHA256:
        raise RuntimeError("WEIGHTS_MANIFEST_SHA256_MISMATCH")
    if manifest.get("schema") != "CAJITA_SIX_DOMAIN_WEIGHT_MANIFEST/1.0":
        raise RuntimeError("WEIGHTS_MANIFEST_SCHEMA_INVALID")
    matches = [item for item in manifest.get("artifacts", []) if item.get("path") == asset_rel]
    if len(matches) != 1:
        raise RuntimeError("WEIGHTS_MANIFEST_ENTRY_MISSING_OR_DUPLICATED:" + asset_rel)
    item = matches[0]
    path = (ROOT / asset_rel)
    if path.is_symlink():
        raise RuntimeError("MODEL_ASSET_SYMLINK_REJECTED:" + asset_rel)
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise RuntimeError("MODEL_ASSET_MISSING:" + asset_rel) from exc
    if not resolved.is_relative_to(ROOT.resolve()) or not resolved.is_file():
        raise RuntimeError("MODEL_ASSET_PATH_INVALID:" + asset_rel)
    with resolved.open("rb") as stream:
        prefix = stream.read(200)
    if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError("MODEL_ASSET_IS_LFS_POINTER_NOT_DOWNLOADED:" + asset_rel)
    expected_size = int(item.get("bytes", -1))
    actual_size = resolved.stat().st_size
    if actual_size != expected_size:
        raise RuntimeError(f"MODEL_ASSET_SIZE_MISMATCH:{asset_rel}:{actual_size}:{expected_size}")
    digest = sha256_file(resolved)
    expected_digest = str(item.get("sha256", "")).lower()
    if digest.lower() != expected_digest:
        raise RuntimeError("MODEL_ASSET_SHA256_MISMATCH:" + asset_rel)
    return {"path": asset_rel, "bytes": actual_size, "sha256": digest, "manifest_schema": manifest["schema"]}

def audit_asset_presence() -> list[dict[str, Any]]:
    results = []
    for domain_id, spec in DOMAINS.items():
        if not spec["asset"]:
            results.append({"domain_id": domain_id, "asset_check": "NOT_APPLICABLE", "adapter": spec["kind"]})
            continue
        try:
            asset = expected_asset(spec["asset"])
            results.append({"domain_id": domain_id, "asset_check": "PASS", "asset": asset})
        except Exception as exc:
            results.append({"domain_id": domain_id, "asset_check": "FAIL_CLOSED",
                            "reason": str(exc)[:300], "asset_path": spec["asset"]})
    return results

def make_pdf(text: str, destination: pathlib.Path) -> dict[str, Any]:
    """Create a minimal multipage PDF using PDF base-14 Helvetica/WinAnsi, without pip deps."""
    if not text.strip():
        raise ValueError("PDF_TEXT_EMPTY")
    if len(text.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("PDF_TEXT_TOO_LARGE")
    destination = destination.expanduser()
    if destination.exists() and destination.is_symlink():
        raise RuntimeError("PDF_OUTPUT_SYMLINK_REJECTED")
    destination.parent.mkdir(parents=True, exist_ok=True)
    safe_lines: list[bytes] = []
    replacements = 0
    for source_line in text.splitlines() or [text]:
        wrapped = textwrap.wrap(source_line, width=92, replace_whitespace=False, drop_whitespace=True) or [""]
        for line in wrapped:
            encoded = line.encode("cp1252", errors="replace")
            replacements += line.count("\ufffd")
            # Count non-CP1252 code points that the output encoding replaces.
            replacements += sum(1 for ch in line if ord(ch) > 255 and ch.encode("cp1252", errors="replace") == b"?")
            escaped = encoded.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
            escaped = b"".join(bytes((byte,)) if 32 <= byte <= 126 or byte >= 160
                               else (b"\\%03o" % byte) for byte in escaped)
            safe_lines.append(escaped)
    chunks = [safe_lines[i:i + 48] for i in range(0, len(safe_lines), 48)] or [[b""]]
    objects: dict[int, bytes] = {}
    page_ids = [4 + (i * 2) for i in range(len(chunks))]
    content_ids = [page_id + 1 for page_id in page_ids]
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = b" ".join(f"{page_id} 0 R".encode("ascii") for page_id in page_ids)
    objects[2] = b"<< /Type /Pages /Kids [" + kids + f"] /Count {len(chunks)} >>".encode("ascii")
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    for page_id, content_id, lines in zip(page_ids, content_ids, chunks):
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        stream = bytearray(b"BT\n/F1 10 Tf\n50 760 Td\n13 TL\n")
        for line in lines:
            stream += b"(" + line + b") Tj\nT*\n"
        stream += b"ET\n"
        objects[content_id] = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + bytes(stream) + b"endstream"
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (max(objects) + 1)
    for obj_id in range(1, max(objects) + 1):
        offsets[obj_id] = len(pdf)
        pdf += f"{obj_id} 0 obj\n".encode("ascii") + objects[obj_id] + b"\nendobj\n"
    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(offsets)}\n".encode("ascii")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("ascii")
    pdf += f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    with destination.open("wb") as stream:
        stream.write(pdf)
        stream.flush()
        os.fsync(stream.fileno())
    return {"status": "PASS_PDF_CREATED", "output_path": str(destination.resolve()),
            "output_bytes": len(pdf), "output_sha256": hashlib.sha256(pdf).hexdigest(),
            "page_count": len(chunks), "encoding": "WinAnsi/Helvetica", "unicode_replacements": replacements}

def read_pcm_wav(path: pathlib.Path):
    import numpy as np
    path = path.expanduser().resolve(strict=True)
    if not path.is_file() or path.stat().st_size > MAX_INPUT_FILE_BYTES:
        raise RuntimeError("AUDIO_FILE_INVALID_OR_TOO_LARGE")
    with wave.open(str(path), "rb") as wav:
        if wav.getcomptype() != "NONE":
            raise RuntimeError("AUDIO_WAV_MUST_BE_UNCOMPRESSED_PCM")
        channels, width, rate, frame_count = wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
        if channels not in (1, 2) or width not in (1, 2, 4) or not (8000 <= rate <= 96000):
            raise RuntimeError("AUDIO_WAV_FORMAT_UNSUPPORTED")
        if frame_count <= 0 or frame_count / rate > 30:
            raise RuntimeError("AUDIO_DURATION_MUST_BE_0_TO_30_SECONDS")
        raw = wav.readframes(frame_count)
    if width == 1:
        values = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 2:
        values = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    else:
        values = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    if channels == 2:
        values = values.reshape(-1, 2).mean(axis=1)
    if rate != 16000:
        old_x = np.arange(values.shape[0], dtype=np.float64) / rate
        new_len = max(1, int(round(values.shape[0] * 16000 / rate)))
        new_x = np.arange(new_len, dtype=np.float64) / 16000
        values = np.interp(new_x, old_x, values).astype(np.float32)
    return values.astype(np.float32), {"sample_rate_input": rate, "sample_rate_model": 16000,
                                      "input_channels": channels, "duration_seconds": round(frame_count / rate, 3)}

def load_translation_lang_map(tokenizer):
    mapping = {}
    for token in getattr(tokenizer, "additional_special_tokens", None) or []:
        if isinstance(token, str) and token.startswith("__") and token.endswith("__") and len(token) > 4:
            lang = token[2:-2]
            token_id = tokenizer.convert_tokens_to_ids(token)
            if isinstance(token_id, int) and token_id >= 0 and lang:
                mapping[lang] = token_id
    if not mapping:
        raise RuntimeError("PACKAGED_TOKENIZER_LANGUAGE_MAP_EMPTY")
    return mapping

def apply_low_memory_document_profile(processor) -> dict[str, Any]:
    """Bound Idefics3 image tiles so one-page OCR does not upscale/split to 2K."""
    image_processor = getattr(processor, "image_processor", None)
    if image_processor is None:
        raise RuntimeError("DOCUMENT_IMAGE_PROCESSOR_MISSING")
    # The packaged preprocessor defaults to longest_edge=2048 with image splitting,
    # which can turn one page into many 512px crops and exceed the 1 GiB profile.
    # This candidate explicitly trades resolution for a bounded single-image path.
    image_processor.size = {"longest_edge": 512}
    image_processor.max_image_size = {"longest_edge": 512}
    image_processor.do_image_splitting = False
    return {"profile_id": "LOW_MEMORY_512_NO_SPLITS", "longest_edge_px": 512,
            "max_image_edge_px": 512, "image_splitting": False,
            "quality_equivalence": "NOT_ESTABLISHED"}

def run_model_task(domain_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    spec = DOMAINS[domain_id]
    action = str(payload.get("action", "infer"))
    if action == "generate_pdf" and domain_id == "D05_INTELIGENCIA_DOCUMENTAL":
        text = str(payload.get("text", ""))
        output_path = pathlib.Path(str(payload.get("output_file", "")))
        if not str(payload.get("output_file", "")).strip():
            raise RuntimeError("PDF_OUTPUT_FILE_REQUIRED")
        return {**make_pdf(text, output_path), "domain_id": domain_id, "model_loaded": False,
                "capability": "pdf_generation", "task_adapter": "standard-library"}
    if domain_id == "D02_ORQUESTACION":
        mod = load_module(spec["module"], "cajita_cli_registry_adapter")
        result = mod.selftest()
        if result.get("status") != "PASS" or not result.get("manifest_present"):
            raise RuntimeError("ORCHESTRATOR_SELFTEST_FAILED")
        return {"status": "PASS_ORCHESTRATOR_PREFLIGHT", "domain_id": domain_id,
                "operation": "manifest-and-eight-cli-catalog-selftest",
                "manifest_present": result["manifest_present"], "project_mutations": False,
                "external_cli_installation_proven": False, "task_adapter": "diagnostic/control-plane"}
    if domain_id == "D01_CEREBRO":
        import torch
        from transformers import AutoTokenizer
        mod = load_module(spec["module"], "cajita_cerebro_adapter")
        tokenizer = model = enc = generated = None
        try:
            tokenizer = AutoTokenizer.from_pretrained(spec["module"].parent, local_files_only=True)
            model = mod.build_model()
            prompt = str(payload.get("text", "Responde con una frase breve y directa."))
            if not prompt.strip():
                raise RuntimeError("PROMPT_EMPTY")
            max_new = max(1, min(int(payload.get("max_new_tokens", 8)), 24))
            enc = tokenizer(prompt, return_tensors="pt")
            with torch.inference_mode():
                generated = model.generate(enc["input_ids"], attention_mask=enc.get("attention_mask"),
                                           max_new_tokens=max_new, do_sample=False, use_cache=False)
            count = int(generated.shape[-1] - enc["input_ids"].shape[-1])
            if count < 1:
                raise RuntimeError("CEREBRO_GENERATED_NO_NEW_TOKENS")
            text = tokenizer.decode(generated[0, enc["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
            if not text:
                raise RuntimeError("CEREBRO_OUTPUT_EMPTY")
            result = {"status": "PASS_TEXT_GENERATION", "domain_id": domain_id, "model_type": model.config.model_type,
                      "generated_token_count": count, "output_text": text, "model_loaded": True,
                      "task_adapter": "local-lowrank-generation"}
            return result
        finally:
            del generated, enc, model, tokenizer
            gc.collect()
            try:
                import ctypes
                ctypes.CDLL(None).malloc_trim(0)
            except Exception:
                pass
    if domain_id == "D03_TRANSCRIPCION":
        import torch
        import numpy as np
        from transformers import WhisperProcessor
        mod = load_module(spec["module"], "cajita_transcription_adapter")
        processor = model = inputs = generated = None
        try:
            input_path = pathlib.Path(str(payload.get("input_file", "")))
            if not str(payload.get("input_file", "")).strip():
                raise RuntimeError("AUDIO_INPUT_FILE_REQUIRED")
            audio, audio_meta = read_pcm_wav(input_path)
            processor = WhisperProcessor.from_pretrained(spec["module"].parent, local_files_only=True)
            model = mod.load_candidate()
            inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
            inputs["input_features"] = inputs["input_features"].to(dtype=torch.float32)
            max_new = max(1, min(int(payload.get("max_new_tokens", 16)), 64))
            with torch.inference_mode():
                generated = model.generate(**inputs, max_new_tokens=max_new, do_sample=False)
            if not isinstance(generated, torch.Tensor) or generated.ndim != 2 or generated.shape[0] != 1:
                raise RuntimeError("MALFORMED_TRANSCRIPTION_OUTPUT")
            decoded = processor.batch_decode(generated, skip_special_tokens=True)
            text = decoded[0] if decoded else ""
            return {"status": "PASS_TRANSCRIPTION_INFERENCE", "domain_id": domain_id,
                    "model_type": model.config.model_type, "generated_token_count": int(generated.shape[-1]),
                    "output_text": text, "audio": audio_meta, "model_loaded": True,
                    "quality_metric": "WER_NOT_EVALUATED", "task_adapter": "local-lowrank-whisper"}
        finally:
            del generated, inputs, model, processor
            gc.collect()
            try:
                import ctypes
                ctypes.CDLL(None).malloc_trim(0)
            except Exception:
                pass
    if domain_id == "D04_TRADUCTOR_INTELIGENTE":
        import torch
        from transformers import AutoProcessor
        mod = load_module(spec["module"], "cajita_translation_adapter")
        processor = model = inputs = generated = None
        try:
            text_input = str(payload.get("text", "Hello world."))
            source_lang = str(payload.get("source_lang", "eng"))
            target_lang = str(payload.get("target_lang", "spa"))
            if not text_input.strip():
                raise RuntimeError("TRANSLATION_TEXT_EMPTY")
            processor = AutoProcessor.from_pretrained(spec["module"].parent, local_files_only=True)
            model = mod.load_candidate()
            tokenizer = getattr(processor, "tokenizer", None)
            if tokenizer is None:
                raise RuntimeError("TOKENIZER_REQUIRED_FOR_TEXT_LANGUAGE_MAP")
            lang_map = load_translation_lang_map(tokenizer)
            if target_lang not in lang_map:
                raise RuntimeError("TARGET_LANGUAGE_NOT_IN_PACKAGED_TOKENIZER:" + target_lang)
            if source_lang not in lang_map:
                raise RuntimeError("SOURCE_LANGUAGE_NOT_IN_PACKAGED_TOKENIZER:" + source_lang)
            model.generation_config.text_decoder_lang_to_code_id = lang_map
            inputs = processor(text=text_input, src_lang=source_lang, return_tensors="pt")
            max_new = max(1, min(int(payload.get("max_new_tokens", 8)), 32))
            with torch.inference_mode():
                generated = model.generate(**inputs, tgt_lang=target_lang, max_new_tokens=max_new, generate_speech=False)
            sequences = generated.sequences if hasattr(generated, "sequences") else generated
            if not isinstance(sequences, torch.Tensor) or sequences.ndim != 2 or sequences.shape[0] != 1:
                raise RuntimeError("MALFORMED_TRANSLATION_OUTPUT")
            decoded = processor.batch_decode(sequences, skip_special_tokens=True)
            text_out = decoded[0].strip() if decoded else ""
            if not text_out:
                raise RuntimeError("TRANSLATION_OUTPUT_EMPTY")
            return {"status": "PASS_TEXT_TRANSLATION", "domain_id": domain_id,
                    "model_type": model.config.model_type, "input_token_count": int(inputs["input_ids"].shape[-1]),
                    "generated_token_count": int(sequences.shape[-1]), "output_text": text_out,
                    "source_lang": source_lang, "target_lang": target_lang, "model_loaded": True,
                    "quality_metric": "TRANSLATION_QUALITY_NOT_EVALUATED",
                    "task_adapter": "local-lowrank-seamless-m4t"}
        finally:
            del generated, inputs, model, processor
            gc.collect()
            try:
                import ctypes
                ctypes.CDLL(None).malloc_trim(0)
            except Exception:
                pass
    if domain_id == "D05_INTELIGENCIA_DOCUMENTAL":
        import torch
        from transformers import AutoProcessor
        mod = load_module(spec["module"], "cajita_document_adapter")
        processor = model = image = inputs = generated = pdfdoc = page = bitmap = None
        try:
            input_value = str(payload.get("input_file", ""))
            if not input_value:
                raise RuntimeError("DOCUMENT_INPUT_FILE_REQUIRED")
            input_path = pathlib.Path(input_value).expanduser().resolve(strict=True)
            if not input_path.is_file() or input_path.stat().st_size > MAX_INPUT_FILE_BYTES:
                raise RuntimeError("DOCUMENT_FILE_INVALID_OR_TOO_LARGE")
            if input_path.suffix.casefold() == ".pdf":
                try:
                    import pypdfium2 as pdfium
                except ImportError as exc:
                    raise RuntimeError("PDF_RENDERER_PYPDFIUM2_NOT_INSTALLED") from exc
                pdfdoc = pdfium.PdfDocument(str(input_path))
                if len(pdfdoc) < 1:
                    raise RuntimeError("PDF_HAS_NO_PAGES")
                page = pdfdoc[0]
                bitmap = page.render(scale=1.0)
                image = bitmap.to_pil().convert("RGB")
            else:
                from PIL import Image
                image = Image.open(input_path).convert("RGB")
            processor = AutoProcessor.from_pretrained(spec["module"].parent, local_files_only=True, trust_remote_code=False)
            image_profile = apply_low_memory_document_profile(processor)
            model, meta = mod.load_candidate(str(spec["module"].parent))
            prompt = str(payload.get("text", "Extract the visible text and structure from this page."))
            messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
            try:
                inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True,
                                                       return_dict=True, return_tensors="pt")
            except Exception:
                inputs = processor(images=image, text=prompt, return_tensors="pt")
            inputs = {key: (value.to("cpu") if isinstance(value, torch.Tensor) else value)
                      for key, value in inputs.items()}
            max_new = max(1, min(int(payload.get("max_new_tokens", 32)), 64))
            with torch.inference_mode():
                generated = model.generate(**inputs, max_new_tokens=max_new, do_sample=False)
            decoded = processor.batch_decode(generated, skip_special_tokens=False)
            text_out = decoded[0].strip() if decoded else ""
            if len(text_out) < 4:
                raise RuntimeError("DOCUMENT_EXTRACTION_OUTPUT_EMPTY_OR_SHORT")
            return {"status": "PASS_DOCUMENT_EXTRACTION", "domain_id": domain_id,
                    "candidate_id": meta.get("candidate_id"), "generated_token_count": int(generated.shape[-1]),
                    "output_text": text_out, "document_kind": input_path.suffix.casefold().lstrip("."),
                    "model_loaded": True, "image_processing_profile": image_profile,
                    "quality_metric": "OCR_LAYOUT_QUALITY_NOT_EVALUATED",
                    "task_adapter": "local-quantized-granite-docling"}
        finally:
            del generated, inputs, model, processor, bitmap, page, pdfdoc, image
            gc.collect()
            try:
                import ctypes
                ctypes.CDLL(None).malloc_trim(0)
            except Exception:
                pass
    if domain_id == "D06_SISTEMA_INTELIGENTE":
        import torch
        from transformers import AutoTokenizer
        mod = load_module(spec["module"], "cajita_reasoning_adapter")
        tokenizer = model = tokens = generated = None
        try:
            prompt = str(payload.get("text", "State one concise reason for checking evidence."))
            if not prompt.strip():
                raise RuntimeError("REASONING_PROMPT_EMPTY")
            tokenizer = AutoTokenizer.from_pretrained(spec["module"].parent, local_files_only=True)
            model = mod.load_candidate()
            tokens = tokenizer(prompt, return_tensors="pt")
            max_new = max(1, min(int(payload.get("max_new_tokens", 8)), 32))
            with torch.inference_mode():
                generated = model.generate(input_ids=tokens["input_ids"],
                                           attention_mask=tokens.get("attention_mask"),
                                           max_new_tokens=max_new, do_sample=False, use_cache=False)
            count = int(generated.shape[-1] - tokens["input_ids"].shape[-1])
            if count < 1:
                raise RuntimeError("REASONING_MODEL_GENERATED_NO_NEW_TOKENS")
            text_out = tokenizer.decode(generated[0, tokens["input_ids"].shape[-1]:],
                                        skip_special_tokens=True).strip()
            if not text_out:
                raise RuntimeError("REASONING_OUTPUT_EMPTY")
            return {"status": "PASS_REASONING_TEXT_GENERATION", "domain_id": domain_id,
                    "model_type": model.config.model_type, "generated_token_count": count,
                    "output_text": text_out, "model_loaded": True,
                    "quality_metric": "REASONING_QUALITY_NOT_EVALUATED",
                    "task_adapter": "local-lowrank-qwen3"}
        finally:
            del generated, tokens, model, tokenizer
            gc.collect()
            try:
                import ctypes
                ctypes.CDLL(None).malloc_trim(0)
            except Exception:
                pass
    raise RuntimeError("UNKNOWN_DOMAIN:" + domain_id)

def worker_main(domain_id: str) -> int:
    affinity = set_single_cpu_affinity()
    verified_asset = False
    started = time.monotonic()
    try:
        if domain_id not in DOMAINS:
            raise RuntimeError("UNKNOWN_DOMAIN:" + domain_id)
        raw = sys.stdin.read()
        payload = json.loads(raw or "{}")
        if not isinstance(payload, dict):
            raise RuntimeError("WORKER_INPUT_MUST_BE_JSON_OBJECT")
        if payload.get("action") != "generate_pdf":
            # Verify byte identity at the point of use, not merely on a prior checkout.
            asset_rel = DOMAINS[domain_id]["asset"]
            if asset_rel:
                expected_asset(asset_rel)
                verified_asset = True
        task_result = run_model_task(domain_id, payload)
        output_text = str(task_result.pop("output_text", ""))
        result = {
            "schema": SCHEMA, "operation": "worker-result", "domain_id": domain_id,
            "status": task_result.pop("status", "PASS"),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "task_result": task_result,
            "output_sha256": sha256_text(output_text) if output_text else None,
            "output_chars": len(output_text),
            "output_text": output_text,
            "peak_rss_mib": peak_rss_mib(),
            "rss_after_model_unload_mib": current_rss_mib(),
            "model_payload_hash_verified": verified_asset,
            "model_asset_validation": "PASS" if verified_asset else "NOT_APPLICABLE",
            "cpu_affinity": affinity,
            "certification": "NOT_GRANTED",
        }
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
        return 0
    except BaseException as exc:
        gc.collect()
        result = {"schema": SCHEMA, "operation": "worker-result", "domain_id": domain_id,
                  "status": "FAIL_CLOSED", "elapsed_seconds": round(time.monotonic() - started, 3),
                  "error_type": type(exc).__name__, "reason": str(exc)[:500],
                  "peak_rss_mib": peak_rss_mib(), "rss_after_model_unload_mib": current_rss_mib(),
                  "model_payload_hash_verified": False, "model_asset_validation": "FAILED",
                  "cpu_affinity": affinity, "certification": "NOT_GRANTED"}
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
        return 2

def make_synthetic_audio(path: pathlib.Path) -> None:
    sample_rate = 16000
    frames = b"\x00\x00" * sample_rate
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)

def make_synthetic_image(path: pathlib.Path) -> None:
    # Binary PPM keeps fixture creation standard-library-only; PIL handles it in the worker.
    width = height = 64
    pixels = bytes([255, 255, 255]) * width * height
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode("ascii") + pixels)

def process_rss_mib(pid: int) -> float | None:
    return current_rss_mib(pid)

def run_stage(domain_id: str, payload: dict[str, Any], max_rss_mib: int,
              timeout_seconds: int) -> dict[str, Any]:
    if domain_id not in DOMAINS:
        return {"domain_id": domain_id, "status": "FAIL_CLOSED", "reason": "UNKNOWN_DOMAIN"}
    started = time.monotonic()
    spec = DOMAINS[domain_id]
    asset = None
    if spec["asset"] and payload.get("action") != "generate_pdf":
        try:
            asset = expected_asset(spec["asset"])
        except Exception as exc:
            return {"domain_id": domain_id, "status": "BLOCKED_ASSET_VALIDATION",
                    "reason": str(exc)[:500], "worker_started": False,
                    "certification": "NOT_GRANTED"}
    input_summary = None
    input_value = payload.get("input_file")
    if input_value:
        try:
            input_path = pathlib.Path(str(input_value)).expanduser()
            if input_path.is_symlink():
                raise RuntimeError("INPUT_FILE_SYMLINK_REJECTED")
            input_path = input_path.resolve(strict=True)
            if not input_path.is_file() or input_path.stat().st_size > MAX_INPUT_FILE_BYTES:
                raise RuntimeError("INPUT_FILE_INVALID_OR_TOO_LARGE")
            input_summary = {"bytes": input_path.stat().st_size, "sha256": sha256_file(input_path)}
        except Exception as exc:
            return {"domain_id": domain_id, "status": "BLOCKED_INPUT_VALIDATION",
                    "reason": str(exc)[:300], "worker_started": False, "certification": "NOT_GRANTED"}
    env = os.environ.copy()
    env.update({"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                "NUMEXPR_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false",
                "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    if env.get("GITHUB_SHA"):
        commit_sha = env["GITHUB_SHA"]
    else:
        commit_sha = "UNAVAILABLE"
    command = [sys.executable, "-B", str(pathlib.Path(__file__).resolve()), "worker", "--domain", domain_id]
    # Temporary anonymous files prevent large model logs from filling pipes or being persisted.
    with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(mode="w+b") as stderr_file:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout_file, stderr=stderr_file,
                                cwd=str(ROOT), env=env, close_fds=True)
        worker_pid = proc.pid
        try:
            assert proc.stdin is not None
            proc.stdin.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        peak_sample = 0.0
        peak_supervisor_sample = current_rss_mib() or 0.0
        peak_combined_sample = peak_supervisor_sample
        worker_limit_hit = False
        combined_limit_hit = False
        timeout_hit = False
        while proc.poll() is None:
            sample = process_rss_mib(worker_pid)
            supervisor_sample = current_rss_mib() or 0.0
            peak_supervisor_sample = max(peak_supervisor_sample, supervisor_sample)
            if sample is not None:
                peak_sample = max(peak_sample, sample)
                combined = sample + supervisor_sample
                peak_combined_sample = max(peak_combined_sample, combined)
                if sample > max_rss_mib:
                    worker_limit_hit = True
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break
                if combined > MAX_PARENT_PLUS_WORKER_RSS_MIB:
                    combined_limit_hit = True
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break
            if time.monotonic() - started > timeout_seconds:
                timeout_hit = True
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break
            time.sleep(0.05)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        stdout_file.seek(0)
        stdout = stdout_file.read().decode("utf-8", errors="replace")
        stderr_file.seek(0)
        stderr = stderr_file.read().decode("utf-8", errors="replace")
    pid_reaped = not pathlib.Path(f"/proc/{worker_pid}").exists() if sys.platform.startswith("linux") else proc.poll() is not None
    worker_result = None
    for line in reversed(stdout.splitlines()):
        try:
            candidate = json.loads(line)
            if isinstance(candidate, dict) and candidate.get("operation") == "worker-result":
                worker_result = candidate
                break
        except json.JSONDecodeError:
            continue
    reported_peak = (worker_result or {}).get("peak_rss_mib")
    max_observed = max(peak_sample, float(reported_peak or 0))
    supervisor_peak = round(peak_supervisor_sample, 3)
    combined_peak = round(max(peak_combined_sample, max_observed + supervisor_peak), 3)
    status = "PASS"
    reason = None
    if worker_limit_hit:
        status, reason = "RESOURCE_LIMIT_EXCEEDED", f"WORKER_RSS_EXCEEDED_{max_rss_mib}_MIB"
    elif combined_limit_hit:
        status, reason = "RESOURCE_LIMIT_EXCEEDED", f"GLOBAL_PROCESS_RSS_EXCEEDED_{MAX_PARENT_PLUS_WORKER_RSS_MIB}_MIB"
    elif timeout_hit:
        status, reason = "TIMEOUT", f"STAGE_TIMEOUT_{timeout_seconds}_SECONDS"
    elif proc.returncode != 0 or not worker_result or worker_result.get("status") == "FAIL_CLOSED":
        status = "FAIL"
        reason = (worker_result or {}).get("reason") or f"WORKER_EXIT_CODE_{proc.returncode}"
    elif max_observed > max_rss_mib:
        status, reason = "RESOURCE_LIMIT_EXCEEDED", f"WORKER_PEAK_RSS_EXCEEDED_{max_rss_mib}_MIB"
    elif combined_peak > MAX_PARENT_PLUS_WORKER_RSS_MIB:
        status, reason = "RESOURCE_LIMIT_EXCEEDED", f"GLOBAL_PROCESS_RSS_EXCEEDED_{MAX_PARENT_PLUS_WORKER_RSS_MIB}_MIB"
    if not pid_reaped:
        status, reason = "FAIL_CLOSED", "WORKER_PROCESS_NOT_REAPED"
    if worker_result and worker_result.get("status", "").startswith("PASS") and status == "PASS":
        operation_status = worker_result["status"]
    else:
        operation_status = status
    output = (worker_result or {}).get("output_text", "")
    report = {
        "schema": SCHEMA, "domain_id": domain_id, "domain_name": spec["name"],
        "status": status, "operation_status": operation_status,
        "reason": reason, "worker_started": True, "worker_pid": worker_pid,
        "worker_pid_reaped": pid_reaped, "worker_exit_code": proc.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "peak_rss_mib": round(max_observed, 3), "worker_rss_limit_mib": max_rss_mib,
        "supervisor_peak_rss_mib": supervisor_peak,
        "peak_combined_parent_worker_rss_mib": combined_peak,
        "combined_parent_worker_rss_limit_mib": MAX_PARENT_PLUS_WORKER_RSS_MIB,
        "global_ram_budget_mib": MAX_GLOBAL_RAM_MIB,
        "rss_after_model_unload_mib": (worker_result or {}).get("rss_after_model_unload_mib"),
        "model_loaded": bool(((worker_result or {}).get("task_result") or {}).get("model_loaded", False)),
        "model_asset": asset,
        "model_payload_hash_verified": bool((asset and asset.get("sha256")) or (worker_result or {}).get("model_payload_hash_verified", False)),
        "model_asset_validation": (worker_result or {}).get("model_asset_validation",
                                   "PASS_PRE_DISPATCH" if asset and asset.get("sha256") else "FAILED_OR_UNAVAILABLE"),
        "worker_cpu_affinity": (worker_result or {}).get("cpu_affinity"),
        "input_file": input_summary,
        "output_sha256": (worker_result or {}).get("output_sha256") or (hashlib.sha256(output.encode("utf-8")).hexdigest() if output else None),
        "output_chars": (worker_result or {}).get("output_chars", 0),
        "worker_error_type": (worker_result or {}).get("error_type"),
        "worker_error_reason": (worker_result or {}).get("reason"),
        "stderr_sha256": sha256_text(stderr) if stderr else None,
        "stderr_excerpt": stderr[-1000:] if status != "PASS" and stderr else None,
        "commit_sha": commit_sha, "captured_at_utc": utc_now(),
        "task_input_persisted": False, "quality_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED",
    }
    # Never expose raw output text in durable reports.
    report.pop("output_text", None)
    return report

def append_audit_trace(path_value: str, report: dict[str, Any], request_text: str = "") -> None:
    path = pathlib.Path(path_value).expanduser()
    if path.exists() and path.is_symlink():
        raise RuntimeError("AUDIT_TRACE_SYMLINK_REJECTED")
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp_utc": utc_now(), "schema": SCHEMA, "domain_id": report.get("domain_id"),
        "operation_status": report.get("operation_status", report.get("status")),
        "request_sha256": sha256_text(request_text) if request_text else None,
        "input_file_sha256": (report.get("input_file") or {}).get("sha256"),
        "input_file_bytes": (report.get("input_file") or {}).get("bytes"),
        "model_asset_sha256": (report.get("model_asset") or {}).get("sha256"),
        "peak_rss_mib": report.get("peak_rss_mib"), "worker_rss_limit_mib": report.get("worker_rss_limit_mib"),
        "worker_pid_reaped": report.get("worker_pid_reaped"), "output_sha256": report.get("output_sha256"),
        "status": report.get("status"), "reason": report.get("reason"), "certification": "NOT_GRANTED",
        "request_body_stored": False,
    }
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())

def run_measurement(domain_id: str, max_rss_mib: int, timeout_seconds: int,
                    trace_file: str | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cajita-adapter-") as temp:
        work = pathlib.Path(temp)
        payload: dict[str, Any] = {}
        if domain_id == "D01_CEREBRO":
            payload = {"action": "infer", "text": "Reply with a short, complete sentence.", "max_new_tokens": 2}
        elif domain_id == "D02_ORQUESTACION":
            payload = {"action": "selftest"}
        elif domain_id == "D03_TRANSCRIPCION":
            audio = work / "synthetic-silent-1s.wav"
            make_synthetic_audio(audio)
            payload = {"action": "transcribe", "input_file": str(audio), "max_new_tokens": 4}
        elif domain_id == "D04_TRADUCTOR_INTELIGENTE":
            payload = {"action": "translate", "text": "Hello world.", "source_lang": "eng", "target_lang": "spa", "max_new_tokens": 4}
        elif domain_id == "D05_INTELIGENCIA_DOCUMENTAL":
            image = work / "synthetic-white-page.ppm"
            make_synthetic_image(image)
            payload = {"action": "extract", "input_file": str(image), "text": "Extract the visible text from this page.", "max_new_tokens": 8}
        elif domain_id == "D06_SISTEMA_INTELIGENTE":
            payload = {"action": "infer", "text": "State one concise reason for checking evidence.", "max_new_tokens": 2}
        report = run_stage(domain_id, payload, max_rss_mib, timeout_seconds)
        if trace_file:
            append_audit_trace(trace_file, report, str(payload.get("text", "")))
        # Domain worker must be reaped before this function can continue to another stage.
        return report

def selftest() -> dict[str, Any]:
    import importlib.util
    asset_reports = audit_asset_presence()
    module_results = []
    for domain_id, spec in DOMAINS.items():
        module_present = spec["module"].is_file() and not spec["module"].is_symlink()
        module_results.append({"domain_id": domain_id, "module_present": module_present,
                               "adapter_status": TASK_ADAPTER_STATUS[spec["capability"]],
                               "model_asset": spec["asset"]})
    dependency_results = {
        name: importlib.util.find_spec(name) is not None
        for name in ("torch", "transformers", "safetensors", "numpy", "PIL", "pypdfium2")
    }
    return {"schema": SCHEMA, "operation": "selftest", "captured_at_utc": utc_now(),
            "domain_count": len(DOMAINS), "domains": module_results,
            "asset_audit": asset_reports, "dependency_presence": dependency_results,
            "worker_rss_limit_mib_default": DEFAULT_WORKER_RSS_LIMIT_MIB,
            "combined_parent_worker_rss_limit_mib": MAX_PARENT_PLUS_WORKER_RSS_MIB,
            "reserved_for_os_and_other_processes_mib": MAX_GLOBAL_RAM_MIB - MAX_PARENT_PLUS_WORKER_RSS_MIB,
            "global_ram_budget_mib": MAX_GLOBAL_RAM_MIB, "cpu_thread_limit": 1,
            "execution_mode": "ONE_DOMAIN_PER_CHILD_PROCESS",
            "unload_evidence_available": sys.platform.startswith("linux"),
            "anti_hallucination_onnx": TASK_ADAPTER_STATUS["anti_hallucination_onnx"],
            "certification": "NOT_GRANTED"}

def write_json_atomic(path_value: str, value: dict[str, Any]) -> None:
    path = pathlib.Path(path_value).expanduser()
    if path.exists() and path.is_symlink():
        raise RuntimeError("REPORT_PATH_SYMLINK_REJECTED")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + f".tmp-{os.getpid()}")
    with temp_path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_path, path)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest", help="inventory adapters, dependencies, weights and LFS materialization")
    sub.add_parser("inventory", help="emit domain-to-adapter registry")
    run_parser = sub.add_parser("run", help="run one functional adapter inside an isolated worker")
    run_parser.add_argument("--domain", required=True, choices=tuple(DOMAINS))
    inp = run_parser.add_mutually_exclusive_group(required=True)
    inp.add_argument("--request-stdin", action="store_true", help="read a JSON request object from stdin")
    inp.add_argument("--request-json", help="read a JSON request object from this file")
    run_parser.add_argument("--max-rss-mib", type=int, default=DEFAULT_WORKER_RSS_LIMIT_MIB)
    run_parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_STAGE_TIMEOUT_SECONDS)
    run_parser.add_argument("--trace-file")
    measure_parser = sub.add_parser("measure", help="run a real minimal inference and measure RSS/unload")
    measure_parser.add_argument("--domain", required=True, choices=tuple(DOMAINS))
    measure_parser.add_argument("--max-rss-mib", type=int, default=DEFAULT_WORKER_RSS_LIMIT_MIB)
    measure_parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_STAGE_TIMEOUT_SECONDS)
    measure_parser.add_argument("--trace-file")
    all_parser = sub.add_parser("measure-all", help="sequential real inference/resource test across all domains")
    all_parser.add_argument("--max-rss-mib", type=int, default=DEFAULT_WORKER_RSS_LIMIT_MIB)
    all_parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_STAGE_TIMEOUT_SECONDS)
    all_parser.add_argument("--report-file", default="artifacts/cajita-resource-evidence.json")
    all_parser.add_argument("--trace-file", default="artifacts/cajita-resource-audit.jsonl")
    pdf_parser = sub.add_parser("generate-pdf", help="create a basic PDF using D05's standard-library output adapter")
    pdf_in = pdf_parser.add_mutually_exclusive_group(required=True)
    pdf_in.add_argument("--text-stdin", action="store_true")
    pdf_in.add_argument("--text-file")
    pdf_parser.add_argument("--output-file", required=True)
    args = parser.parse_args(argv)
    if args.command == "worker":
        parser.error("worker is an internal operation")
    if args.command == "inventory":
        print(json.dumps({"schema": SCHEMA, "domains": DOMAINS and [
            {"domain_id": k, "name": v["name"], "kind": v["kind"], "capability": v["capability"],
             "adapter_status": TASK_ADAPTER_STATUS[v["capability"]], "asset": v["asset"]}
            for k, v in DOMAINS.items()], "certification": "NOT_GRANTED"}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "selftest":
        result = selftest()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if all(d["module_present"] for d in result["domains"]) else 2
    if args.command == "generate-pdf":
        content = sys.stdin.read() if args.text_stdin else pathlib.Path(args.text_file).read_text(encoding="utf-8")
        result = make_pdf(content, pathlib.Path(args.output_file))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "PASS_PDF_CREATED" else 2
    if args.command == "run":
        if not (1 <= args.max_rss_mib < MAX_GLOBAL_RAM_MIB) or not (1 <= args.timeout_seconds <= 3600):
            parser.error("resource ceiling or timeout out of range")
        if args.request_stdin:
            payload = json.loads(sys.stdin.read() or "{}")
        else:
            payload = json.loads(pathlib.Path(args.request_json).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            parser.error("request JSON must be an object")
        report = run_stage(args.domain, payload, args.max_rss_mib, args.timeout_seconds)
        if args.trace_file:
            append_audit_trace(args.trace_file, report, str(payload.get("text", "")))
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["status"] == "PASS" else 2
    if args.command == "measure":
        if not (1 <= args.max_rss_mib < MAX_GLOBAL_RAM_MIB) or not (1 <= args.timeout_seconds <= 3600):
            parser.error("resource ceiling or timeout out of range")
        report = run_measurement(args.domain, args.max_rss_mib, args.timeout_seconds, args.trace_file)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["status"] == "PASS" and report["worker_pid_reaped"] else 2
    if not (1 <= args.max_rss_mib < MAX_GLOBAL_RAM_MIB) or not (1 <= args.timeout_seconds <= 3600):
        parser.error("resource ceiling or timeout out of range")
    results = []
    for domain_id in DOMAINS:
        try:
            report = run_measurement(domain_id, args.max_rss_mib, args.timeout_seconds, args.trace_file)
        except Exception as exc:
            report = {"schema": SCHEMA, "domain_id": domain_id, "status": "FAIL_CLOSED",
                      "reason": type(exc).__name__ + ":" + str(exc)[:400],
                      "worker_started": False, "worker_pid_reaped": True,
                      "captured_at_utc": utc_now(), "certification": "NOT_GRANTED"}
        results.append(report)
    statuses = [item["status"] for item in results]
    evidence = {
        "schema": "CAJITA_RESOURCE_EVIDENCE/1.0", "captured_at_utc": utc_now(),
        "candidate_id": "CAJITA_LUNA_RUNTIME_V9_20261023",
        "commit_sha": os.environ.get("GITHUB_SHA", "UNAVAILABLE"),
        "host": {"platform": platform.platform(), "python": sys.version.split()[0],
                 "cpu_count_logical": os.cpu_count(), "memory_monitor": "/proc/<pid>/status",
                 "cpu_affinity_requested": 1},
        "budgets": {"global_ram_mib": MAX_GLOBAL_RAM_MIB, "worker_rss_mib": args.max_rss_mib,
                    "combined_parent_worker_rss_mib": MAX_PARENT_PLUS_WORKER_RSS_MIB,
                    "reserved_for_os_and_other_processes_mib": MAX_GLOBAL_RAM_MIB - MAX_PARENT_PLUS_WORKER_RSS_MIB,
                    "single_active_domain_process": True, "unload_by_process_exit": True},
        "results": results,
        "summary": {"domain_count": len(results), "passed": statuses.count("PASS"),
                    "failed_or_blocked": len(statuses) - statuses.count("PASS"),
                    "all_worker_pids_reaped": all(item.get("worker_pid_reaped", False) for item in results
                                                   if item.get("worker_started")),
                    "peak_rss_measured_for_successful_stages": all(item.get("peak_rss_mib") is not None
                                                                    for item in results if item["status"] == "PASS")},
        "quality_equivalence": "NOT_ESTABLISHED", "independent_validation": "NOT_RUN",
        "certification": "NOT_GRANTED",
    }
    write_json_atomic(args.report_file, evidence)
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0 if evidence["summary"]["passed"] == len(DOMAINS) and evidence["summary"]["all_worker_pids_reaped"] else 3

if __name__ == "__main__":
    # Allow the monitor to invoke a private worker path without exposing it as a public command.
    if len(sys.argv) >= 2 and sys.argv[1] == "worker":
        wp = argparse.ArgumentParser()
        wp.add_argument("worker")
        wp.add_argument("--domain", required=True)
        wa = wp.parse_args(sys.argv[1:])
        raise SystemExit(worker_main(wa.domain))
    raise SystemExit(main())
