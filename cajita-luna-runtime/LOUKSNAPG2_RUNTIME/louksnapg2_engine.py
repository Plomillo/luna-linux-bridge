#!/usr/bin/env python3
"""LOUKSNAPG2 domain adapters.

This runtime is deliberately source-bound and fail-closed. It uses one pinned,
native GGUF Qwen model behind separate Cerebro, analysis, general-translation and
ancient-language adapters, and a separate pinned whisper.cpp model/runtime for
transcription. It never silently routes ancient-language tasks to the general
translation adapter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

SCHEMA = "LOUKSNAPG2_ENGINE_RUNTIME/1.0"
DOMAIN_IDS = {
    "D01_CEREBRO",
    "D03_TRANSCRIPCION",
    "D04_TRADUCTOR_INTELIGENTE",
    "D04_TRADUCCION_LENGUAS_ANTIGUAS",
    "D06_SISTEMA_INTELIGENTE",
}
LANGUAGES = {
    "eng": "English", "en": "English",
    "spa": "Spanish", "es": "Spanish",
    "fra": "French", "fr": "French",
    "deu": "German", "de": "German",
    "ita": "Italian", "it": "Italian",
    "por": "Portuguese", "pt": "Portuguese",
    "grc": "Ancient Greek (Koine/Ancient Greek)", "la": "Latin", "lat": "Latin",
    "heb": "Biblical Hebrew", "arc": "Biblical Aramaic",
}
ANCIENT_LANGUAGES = {"grc", "lat", "la", "heb", "arc"}
DEFAULT_TARGET_LANG = "eng"
MAX_INPUT_CHARS = 16_384
MAX_AUDIO_BYTES = 32 * 1024 * 1024
MAX_AUDIO_SECONDS = 120
DEFAULT_TOKEN_LIMIT = 96
HARD_TOKEN_LIMIT = 192

EXPECTED_MODELS = {
    "QWEN3_0_6B_Q2_K": {
        "path": "models/Qwen3-0.6B-Q2_K.gguf",
        "repo": "unsloth/Qwen3-0.6B-GGUF",
        "revision": "541d985dbfcdc61a64f8b441419e7c0e126bb6e2",
        "file": "Qwen3-0.6B-Q2_K.gguf",
        "bytes": 296_238_784,
        "sha256": "0e850e08a48e9df1d1e0fc9959157e893215040f673e382c9da4339c74b12d3d",
    },
    "WHISPER_TINY_Q5_1": {
        "path": "models/ggml-tiny-q5_1.bin",
        "repo": "ggerganov/whisper.cpp",
        "revision": "c521a4b02f422512d734391fdf08bb08c0862f68",
        "file": "ggml-tiny-q5_1.bin",
        "bytes": 32_152_673,
        "sha256": "818710568da3ca15689e31a743197b520007872ff9576237bda97bd1b469c3d7",
    },
}

# Bounded phrase concordance for well-known, high-confidence Ancient Latin/Greek
# inputs. Unknown phrases proceed only through the dedicated ancient-language
# adapter and its separate prompt; they never invoke the general-translation route.
ANCIENT_CONCORDANCE = {
    ("lat", "eng", "carpe diem"): {
        "translation": "Seize the day.",
        "source_note": "Horace, Odes 1.11; short-form lexical reference",
    },
    ("la", "eng", "carpe diem"): {
        "translation": "Seize the day.",
        "source_note": "Horace, Odes 1.11; short-form lexical reference",
    },
    ("lat", "eng", "veni vidi vici"): {
        "translation": "I came, I saw, I conquered.",
        "source_note": "Conventional Latin phrase; bounded concordance entry",
    },
    ("la", "eng", "veni vidi vici"): {
        "translation": "I came, I saw, I conquered.",
        "source_note": "Conventional Latin phrase; bounded concordance entry",
    },
    ("grc", "eng", "ἐν ἀρχῇ ἦν ὁ λόγος"): {
        "translation": "In the beginning was the Word.",
        "source_note": "John 1:1, first clause; bounded concordance entry",
    },
}


class EngineRuntimeError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[^\W_]+", value, flags=re.UNICODE))


def normalize_ancient(value: str) -> str:
    value = unicodedata.normalize("NFC", str(value).casefold())
    value = "".join(char for char in value if not unicodedata.category(char).startswith("P"))
    return " ".join(value.split())


def _safe_regular_file(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or rel.as_posix() != relative:
        raise EngineRuntimeError("MODEL_PATH_INVALID")
    path = root.joinpath(*rel.parts)
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise EngineRuntimeError("MODEL_FILE_MISSING_OR_UNSAFE:" + relative)
    return path


def verify_model_files(root: Path) -> dict:
    root = Path(root).resolve(strict=True)
    evidence = {}
    for model_id, spec in EXPECTED_MODELS.items():
        path = _safe_regular_file(root, spec["path"])
        size = path.stat().st_size
        if size != spec["bytes"]:
            raise EngineRuntimeError("MODEL_SIZE_MISMATCH:" + model_id)
        digest = sha256_file(path)
        if digest != spec["sha256"]:
            raise EngineRuntimeError("MODEL_SHA256_MISMATCH:" + model_id)
        evidence[model_id] = {
            "path": spec["path"],
            "bytes": size,
            "sha256": digest,
            "source_repo": spec["repo"],
            "source_revision": spec["revision"],
            "source_file": spec["file"],
            "status": "PASS_SOURCE_IDENTITY",
        }
    return evidence


class LouksnapG2Runtime:
    def __init__(self, runtime_root: Path, *, threads: int = 1):
        self.root = Path(runtime_root).resolve(strict=True)
        if threads != 1:
            raise EngineRuntimeError("CPU_THREAD_BUDGET_MUST_BE_ONE")
        self.threads = 1
        self._llm = None
        self._whisper = None
        self._model_evidence = None

    def preflight(self) -> dict:
        if os.environ.get("LOUKSNAPG2_ALLOW_NETWORK_MODEL_FETCH") == "1":
            # Network-fetch authorization belongs to the externalized asset loader,
            # never to model loading. The model runtime itself is always offline.
            raise EngineRuntimeError("MODEL_RUNTIME_NETWORK_ACCESS_FORBIDDEN")
        self._model_evidence = verify_model_files(self.root)
        return {
            "schema": "LOUKSNAPG2_RUNTIME_PREFLIGHT/1.0",
            "status": "PASS_MODEL_SOURCE_IDENTITIES",
            "thread_count": self.threads,
            "models": self._model_evidence,
            "model_downloaded_at_runtime": False,
            "general_translation_fallback_for_ancient": False,
            "certification": "NOT_GRANTED_BY_PREFLIGHT",
        }

    def _load_llm(self):
        if self._llm is None:
            evidence = verify_model_files(self.root)
            model = _safe_regular_file(self.root, EXPECTED_MODELS["QWEN3_0_6B_Q2_K"]["path"])
            try:
                from llama_cpp import Llama
            except ImportError as exc:
                raise EngineRuntimeError("LLAMA_CPP_PYTHON_DEPENDENCY_MISSING") from exc
            os.environ.setdefault("OMP_NUM_THREADS", "1")
            os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
            os.environ.setdefault("MKL_NUM_THREADS", "1")
            self._llm = Llama(
                model_path=str(model),
                n_ctx=2048,
                n_threads=1,
                n_batch=64,
                use_mmap=True,
                use_mlock=False,
                verbose=False,
                seed=0,
            )
            self._model_evidence = evidence
        return self._llm

    def _generate(self, *, system: str, user: str, max_tokens: int) -> str:
        if not isinstance(user, str) or not user.strip() or len(user) > MAX_INPUT_CHARS:
            raise EngineRuntimeError("TEXT_INPUT_EMPTY_OR_OVER_LIMIT")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= HARD_TOKEN_LIMIT:
            raise EngineRuntimeError("TOKEN_LIMIT_OUT_OF_RANGE")
        llm = self._load_llm()
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.0,
            top_p=1.0,
            repeat_penalty=1.05,
            seed=0,
        )
        try:
            text = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise EngineRuntimeError("LLM_RESPONSE_SCHEMA_INVALID") from exc
        if not isinstance(text, str) or not text.strip():
            raise EngineRuntimeError("LLM_OUTPUT_EMPTY")
        return text.strip()

    def reason(self, prompt: str, *, max_tokens: int = DEFAULT_TOKEN_LIMIT) -> dict:
        output = self._generate(
            system=(
                "You are the reasoning adapter of LOUKSNAPG2. Solve the user task accurately. "
                "For arithmetic or inventory tasks explicitly requested as a final integer, output only "
                "the final integer. Do not invent citations, tools, sources, or model abilities."
            ),
            user=prompt,
            max_tokens=max_tokens,
        )
        return self._result("D01_CEREBRO", "generate_text", output)

    def analyze(self, prompt: str, *, max_tokens: int = DEFAULT_TOKEN_LIMIT) -> dict:
        output = self._generate(
            system=(
                "You are the advanced-analysis adapter of LOUKSNAPG2. Analyze the stated problem, "
                "check intermediate arithmetic, and obey the requested output format. For a request "
                "for a final integer, return only the integer. Do not make up evidence."
            ),
            user=prompt,
            max_tokens=max_tokens,
        )
        return self._result("D06_SISTEMA_INTELIGENTE", "analyze_reasoning", output)

    def translate_general(
        self, text: str, *, src_lang: str = "eng", tgt_lang: str = "spa",
        max_tokens: int = 96,
    ) -> dict:
        src = LANGUAGES.get(src_lang.lower())
        tgt = LANGUAGES.get(tgt_lang.lower())
        if not src or not tgt or src_lang.lower() in ANCIENT_LANGUAGES:
            raise EngineRuntimeError("GENERAL_TRANSLATION_LANGUAGE_NOT_REGISTERED")
        output = self._generate(
            system=(
                "You are the dedicated general-language translation adapter of LOUKSNAPG2. "
                f"Translate from {src} into {tgt}. Preserve meaning, names, numbers and sentence order. "
                "Return only the translation; no explanation, transliteration, quotation marks or alternatives."
            ),
            user=text,
            max_tokens=max_tokens,
        )
        return self._result(
            "D04_TRADUCTOR_INTELIGENTE", "translate_text", output,
            input_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            source_language=src_lang.lower(), target_language=tgt_lang.lower(),
        )

    def translate_ancient(
        self, text: str, *, src_lang: str, tgt_lang: str = "eng",
        max_tokens: int = 128,
    ) -> dict:
        source_code = src_lang.strip().lower()
        target_code = tgt_lang.strip().lower()
        if source_code not in ANCIENT_LANGUAGES:
            raise EngineRuntimeError("ANCIENT_SOURCE_LANGUAGE_NOT_REGISTERED")
        if target_code not in ("eng", "en", "spa", "es"):
            raise EngineRuntimeError("ANCIENT_TARGET_LANGUAGE_NOT_REGISTERED")
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_INPUT_CHARS:
            raise EngineRuntimeError("ANCIENT_TRANSLATION_INPUT_EMPTY_OR_OVER_LIMIT")
        normalized = normalize_ancient(text)
        concordance = ANCIENT_CONCORDANCE.get((source_code, target_code, normalized))
        if concordance:
            output = concordance["translation"]
            source = "BOUNDED_CONCORDANCE"
        else:
            # This is a separate source-language adapter and prompt. There is no
            # call to translate_general and no implicit modern-translation fallback.
            source_name = LANGUAGES[source_code]
            target_name = LANGUAGES[target_code]
            output = self._generate(
                system=(
                    "You are the dedicated ancient-language translation adapter of LOUKSNAPG2. "
                    f"Translate only from {source_name} into {target_name}. Preserve morphology, "
                    "case, verbal tense and ambiguity where meaningful. Do not modernize the text. "
                    "Do not use the general-translation adapter. If the source cannot be interpreted "
                    "confidently, return exactly UNRESOLVED rather than inventing a translation. "
                    "Return only the translation or UNRESOLVED."
                ),
                user=text,
                max_tokens=max_tokens,
            )
            source = "DEDICATED_ANCIENT_LANGUAGE_ADAPTER"
            if normalize_text(output) in {"unresolved", "unknown", "cannot translate", "i cannot translate"}:
                raise EngineRuntimeError("ANCIENT_TRANSLATION_UNRESOLVED")
        return self._result(
            "D04_TRADUCCION_LENGUAS_ANTIGUAS", "translate_ancient_text", output,
            source_language=source_code,
            target_language=target_code,
            ancient_adapter="D04_TRADUCCION_LENGUAS_ANTIGUAS_V1",
            translation_strategy=source,
            general_translation_fallback_selected=False,
            concordance_entry_source=concordance.get("source_note") if concordance else None,
        )

    def transcribe(self, audio_path: Path, *, max_audio_bytes: int = MAX_AUDIO_BYTES) -> dict:
        path = Path(audio_path)
        if path.is_symlink() or not path.is_file():
            raise EngineRuntimeError("AUDIO_FILE_MISSING_OR_UNSAFE")
        if path.stat().st_size < 1 or path.stat().st_size > min(MAX_AUDIO_BYTES, max_audio_bytes):
            raise EngineRuntimeError("AUDIO_SIZE_OUT_OF_RANGE")
        try:
            import wave
            with wave.open(str(path), "rb") as audio:
                channels = audio.getnchannels()
                sample_width = audio.getsampwidth()
                rate = audio.getframerate()
                frames = audio.getnframes()
                duration = frames / rate if rate else 0
        except (wave.Error, OSError):
            raise EngineRuntimeError("AUDIO_WAV_REQUIRED_BY_LOCKED_RUNTIME")
        if channels not in (1, 2) or sample_width not in (2, 4) or rate < 8000 or duration <= 0 or duration > MAX_AUDIO_SECONDS:
            raise EngineRuntimeError("AUDIO_FORMAT_OR_DURATION_OUT_OF_RANGE")
        if self._whisper is None:
            model_path = _safe_regular_file(self.root, EXPECTED_MODELS["WHISPER_TINY_Q5_1"]["path"])
            spec = EXPECTED_MODELS["WHISPER_TINY_Q5_1"]
            if model_path.stat().st_size != spec["bytes"] or sha256_file(model_path) != spec["sha256"]:
                raise EngineRuntimeError("WHISPER_MODEL_SOURCE_IDENTITY_MISMATCH")
            try:
                from pywhispercpp.model import Model
            except ImportError as exc:
                raise EngineRuntimeError("PYWHISPERCPP_DEPENDENCY_MISSING") from exc
            self._whisper = Model(
                str(model_path),
                n_threads=1,
                print_progress=False,
                print_realtime=False,
                print_timestamps=False,
            )
        segments = self._whisper.transcribe(str(path), language="en", translate=False)
        pieces = []
        for segment in segments:
            value = getattr(segment, "text", "")
            if isinstance(value, str) and value.strip():
                pieces.append(value.strip())
        output = " ".join(pieces).strip()
        if not output:
            raise EngineRuntimeError("WHISPER_OUTPUT_EMPTY")
        return self._result(
            "D03_TRANSCRIPCION", "transcribe_audio", output,
            input_sha256=sha256_file(path), audio_bytes=path.stat().st_size,
            audio_duration_seconds=round(duration, 3), sample_rate_hz=rate,
        )

    def route(self, domain_id: str, operation: str, payload: dict) -> dict:
        if domain_id not in DOMAIN_IDS:
            raise EngineRuntimeError("DOMAIN_NOT_REGISTERED")
        if not isinstance(payload, dict):
            raise EngineRuntimeError("TASK_INPUT_NOT_OBJECT")
        if domain_id == "D01_CEREBRO" and operation == "generate_text":
            return self.reason(payload.get("prompt", ""), max_tokens=payload.get("max_new_tokens", DEFAULT_TOKEN_LIMIT))
        if domain_id == "D06_SISTEMA_INTELIGENTE" and operation == "analyze_reasoning":
            return self.analyze(payload.get("prompt", ""), max_tokens=payload.get("max_new_tokens", DEFAULT_TOKEN_LIMIT))
        if domain_id == "D04_TRADUCTOR_INTELIGENTE" and operation == "translate_text":
            return self.translate_general(
                payload.get("text", ""),
                src_lang=payload.get("src_lang", "eng"),
                tgt_lang=payload.get("tgt_lang", "spa"),
                max_tokens=payload.get("max_new_tokens", DEFAULT_TOKEN_LIMIT),
            )
        if domain_id == "D04_TRADUCCION_LENGUAS_ANTIGUAS" and operation == "translate_ancient_text":
            return self.translate_ancient(
                payload.get("text", ""),
                src_lang=payload.get("src_lang", ""),
                tgt_lang=payload.get("tgt_lang", "eng"),
                max_tokens=payload.get("max_new_tokens", DEFAULT_TOKEN_LIMIT),
            )
        if domain_id == "D03_TRANSCRIPCION" and operation == "transcribe_audio":
            return self.transcribe(Path(payload.get("audio_path", "")))
        raise EngineRuntimeError("DOMAIN_OPERATION_PAIR_NOT_REGISTERED")

    def _result(self, domain_id: str, operation: str, output_text: str, **extra) -> dict:
        return {
            "schema": "LOUKSNAPG2_TASK_RESULT/1.0",
            "status": "PASS_EXECUTION",
            "execution_authorized": True,
            "domain_id": domain_id,
            "operation": operation,
            "output_text": output_text,
            "output_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            "model_source_evidence": self._model_evidence or verify_model_files(self.root),
            "semantic_quality_equivalence_to_full_size_original": "NOT_ESTABLISHED",
            "certification": "NOT_GRANTED_BY_RUNTIME_CALL",
            **extra,
        }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=Path(__file__).resolve().parent)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    run = sub.add_parser("task")
    run.add_argument("--domain", required=True)
    run.add_argument("--operation", required=True)
    run.add_argument("--input-json", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        runtime = LouksnapG2Runtime(args.runtime_root, threads=1)
        if args.command == "preflight":
            result = runtime.preflight()
        else:
            row = json.loads(args.input_json.read_text(encoding="utf-8"))
            result = runtime.route(args.domain, args.operation, row)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        result = {
            "schema": "LOUKSNAPG2_TASK_RESULT/1.0",
            "status": "FAIL_CLOSED",
            "execution_authorized": False,
            "reason": type(exc).__name__ + ":" + str(exc)[:300],
            "general_translation_fallback_selected": False,
            "certification": "NOT_GRANTED",
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
