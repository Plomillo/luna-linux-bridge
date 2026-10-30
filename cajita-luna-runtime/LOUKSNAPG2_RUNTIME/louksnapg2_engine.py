#!/usr/bin/env python3
"""LOUKSNAPG2 domain router over the original Cajita low-rank model runtimes.

The existing GPT-OSS, Whisper, SeamlessM4T v2 and Qwen3 source adapters and their
weight files are preserved and executed unchanged. Only the missing ancient-language
consumer adapter is added here; it uses a dedicated task contract/prompt over the
existing GPT-OSS source runtime and never calls the general translation adapter.
No new model is downloaded and this module performs no network access.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

SCHEMA = "LOUKSNAPG2_ENGINE_RUNTIME/2.0"
CAJITA_TASK_SCHEMA = "CAJITA_TASK_REQUEST/1.0"
MAX_INPUT_CHARS = 16_384
MAX_NEW_TOKENS = 128
MAX_TIMEOUT_SECONDS = 600
DOMAIN_IDS = {
    "D01_CEREBRO",
    "D03_TRANSCRIPCION",
    "D04_TRADUCTOR_INTELIGENTE",
    "D04_TRADUCCION_LENGUAS_ANTIGUAS",
    "D05_INTELIGENCIA_DOCUMENTAL",
    "D06_SISTEMA_INTELIGENTE",
}
NATIVE_ROUTES = {
    ("D01_CEREBRO", "generate_text"): {
        "target_id": "D01_CEREBRO_ROOT",
        "adapter_id": "CAJITA_CEREBRO_TEXT_GENERATION/1.0",
        "source_domain": "D01_CEREBRO",
        "source_model": "GPT-OSS compactado — rank-1 INT8 factors",
    },
    ("D06_SISTEMA_INTELIGENTE", "analyze_reasoning"): {
        "target_id": "D06_ANALISIS_AVANZADO",
        "adapter_id": "CAJITA_QWEN3_REASONING/1.0",
        "source_domain": "D06_SISTEMA_INTELIGENTE",
        "source_model": "Qwen3 compactado — low-rank INT8 factors",
    },
    ("D04_TRADUCTOR_INTELIGENTE", "translate_text"): {
        "target_id": "D04_TRADUCCION_GENERAL",
        "adapter_id": "CAJITA_SEAMLESS_TRANSLATION/1.0",
        "source_domain": "D04_TRADUCTOR_INTELIGENTE",
        "source_model": "SeamlessM4T v2 compactado — low-rank INT8 factors",
    },
    ("D05_INTELIGENCIA_DOCUMENTAL", "extract_document_image"): {
        "target_id": "D05_DOCLING",
        "adapter_id": "CAJITA_DOCLING_IMAGE_EXTRACTION/1.0",
        "source_domain": "D05_INTELIGENCIA_DOCUMENTAL",
        "source_model": "Granite Docling compactado — packed quantized weights",
    },
    ("D03_TRANSCRIPCION", "transcribe_audio"): {
        "target_id": "D03_TRANSCRIPCION_ROOT",
        "adapter_id": "CAJITA_WHISPER_TRANSCRIPTION/1.0",
        "source_domain": "D03_TRANSCRIPCION",
        "source_model": "Whisper compactado — low-rank INT8 factors",
    },
}
ANCIENT_TARGETS = {
    "lat": "Latin",
    "la": "Latin",
    "grc": "Ancient Greek",
    "heb": "Biblical Hebrew",
    "arc": "Biblical Aramaic",
}
TARGET_LANGUAGES = {"eng": "English", "en": "English", "spa": "Spanish", "es": "Spanish"}


class EngineRuntimeError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _cajita_root(root: Path) -> Path:
    root = Path(root).resolve(strict=True)
    if root.name == "LOUKSNAPG2_RUNTIME":
        root = root.parent
    if not (root / "cajita_task_adapters.py").is_file():
        raise EngineRuntimeError("ORIGINAL_CAJITA_TASK_ADAPTERS_MISSING")
    return root


def _load_native_adapter(root: Path):
    root = _cajita_root(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        import cajita_task_adapters
    except Exception as exc:
        raise EngineRuntimeError("ORIGINAL_CAJITA_TASK_ADAPTER_IMPORT_FAILED:" + type(exc).__name__) from exc
    return cajita_task_adapters


def verify_model_files(root: Path) -> dict:
    """Verify original in-artifact model weights through the source-bound manifests."""
    adapter = _load_native_adapter(root)
    evidence = {}
    for domain in ("D01_CEREBRO", "D03_TRANSCRIPCION", "D04_TRADUCTOR_INTELIGENTE", "D05_INTELIGENCIA_DOCUMENTAL", "D06_SISTEMA_INTELIGENTE"):
        try:
            evidence[domain] = adapter.verify_integrity(_cajita_root(root), domain)
        except Exception as exc:
            raise EngineRuntimeError("ORIGINAL_MODEL_SOURCE_IDENTITY_FAILED:" + domain + ":" + str(exc)[:200]) from exc
    return evidence


class LouksnapG2Runtime:
    """Public router. All model execution is delegated to unchanged Cajita adapters."""

    def __init__(self, root: Path, threads: int = 1):
        if isinstance(threads, bool) or threads != 1:
            raise EngineRuntimeError("CPU_THREAD_BUDGET_MUST_BE_ONE")
        self.root = _cajita_root(Path(root))
        self.threads = 1
        self._adapter_module = None
        self._model_evidence = None

    def preflight(self) -> dict:
        evidence = verify_model_files(self.root)
        manifest = self.root / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
        if manifest.is_symlink() or not manifest.is_file():
            raise EngineRuntimeError("ORIGINAL_MODEL_WEIGHT_MANIFEST_MISSING")
        self._model_evidence = evidence
        return {
            "schema": "LOUKSNAPG2_RUNTIME_PREFLIGHT/2.0",
            "status": "PASS_MODEL_SOURCE_IDENTITIES",
            "thread_count": self.threads,
            "source_model_policy": "REUSE_ORIGINAL_CAJITA_LOW_RANK_WEIGHTS",
            "new_external_model_fetch_performed": False,
            "models": evidence,
            "required_domains": {
                "D01_CEREBRO": "GPT-OSS compacted native adapter",
                "D06_SISTEMA_INTELIGENTE": "Qwen3 compacted native adapter",
                "D04_TRADUCTOR_INTELIGENTE": "SeamlessM4T v2 compacted native adapter",
                "D05_INTELIGENCIA_DOCUMENTAL": "Granite Docling packed-weight image/document extraction adapter",
                "D04_TRADUCCION_LENGUAS_ANTIGUAS": "Dedicated domain prompt over existing GPT-OSS adapter; no general-translation fallback",
                "D03_TRANSCRIPCION": "Whisper compacted native adapter",
            },
            "general_translation_fallback_for_ancient": False,
            "certification": "NOT_GRANTED_BY_PREFLIGHT",
        }

    def _execute_original(self, domain_id: str, operation: str, payload: dict, *, task_id: str, max_tokens: int) -> dict:
        route = NATIVE_ROUTES.get((domain_id, operation))
        if route is None:
            raise EngineRuntimeError("DOMAIN_OPERATION_PAIR_NOT_REGISTERED")
        if not isinstance(payload, dict):
            raise EngineRuntimeError("TASK_INPUT_NOT_OBJECT")
        adapter = self._adapter_module or _load_native_adapter(self.root)
        self._adapter_module = adapter
        request = {
            "schema": CAJITA_TASK_SCHEMA,
            "task_id": task_id,
            "domain_id": domain_id,
            "operation": operation,
            "input": dict(payload),
            "limits": {"timeout_seconds": MAX_TIMEOUT_SECONDS, "max_new_tokens": max_tokens},
        }
        try:
            result, exit_code = adapter.execute_task(request, self.root, timeout_cap=MAX_TIMEOUT_SECONDS)
        except Exception as exc:
            raise EngineRuntimeError("ORIGINAL_CAJITA_RUNTIME_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)[:200]) from exc
        if exit_code != 0 or result.get("status") != "PASS_FUNCTIONAL_EXECUTION" or result.get("execution_authorized") is not True:
            reason = str(result.get("reason") or result.get("status") or "UNKNOWN")[:300]
            diagnostic_suffix = ""
            # Child output is visible only for explicit CI diagnostics on synthetic tasks.
            if os.environ.get("CAJITA_E2E_DIAGNOSTICS") == "1":
                details = []
                for key in ("diagnostic_stderr_tail", "diagnostic_stdout_tail"):
                    value = result.get(key)
                    if isinstance(value, str) and value.strip():
                        details.append(key + "=" + value[-800:])
                if details:
                    diagnostic_suffix = "|DIAGNOSTICS|" + "|".join(details)
            raise EngineRuntimeError("ORIGINAL_CAJITA_RUNTIME_NOT_PASS:" + reason + diagnostic_suffix)
        output = result.get("output_text")
        if not isinstance(output, str) or not output.strip():
            raise EngineRuntimeError("ORIGINAL_CAJITA_RUNTIME_OUTPUT_EMPTY")
        self._model_evidence = self._model_evidence or verify_model_files(self.root)
        return {
            "schema": "LOUKSNAPG2_TASK_RESULT/2.0",
            "status": "PASS_EXECUTION",
            "execution_authorized": True,
            "domain_id": domain_id,
            "operation": operation,
            "target_id": route["target_id"],
            "adapter_id": route["adapter_id"],
            "output_text": output,
            "output_sha256": sha256_bytes(output.encode("utf-8")),
            "model_source_evidence": result.get("integrity", {}),
            "entrypoint_sha256": result.get("entrypoint_sha256"),
            "source_model_id": route["source_model"],
            "source_runtime_status": result.get("model_runtime_status"),
            "generated_token_count": result.get("generated_token_count"),
            "general_translation_fallback_selected": False,
            "semantic_quality_equivalence_to_full_size_original": "NOT_ESTABLISHED",
            "original_adapter_result": result,
            "certification": "NOT_GRANTED_BY_RUNTIME_CALL",
        }

    def reason(self, prompt: str, *, max_tokens: int = 64, task_id: str = "brain") -> dict:
        return self._execute_original(
            "D01_CEREBRO", "generate_text", {"prompt": prompt},
            task_id=task_id, max_tokens=max_tokens,
        )

    def analyze(self, prompt: str, *, max_tokens: int = 64, task_id: str = "analysis") -> dict:
        return self._execute_original(
            "D06_SISTEMA_INTELIGENTE", "analyze_reasoning", {"prompt": prompt},
            task_id=task_id, max_tokens=max_tokens,
        )

    def translate_general(
        self, text: str, *, src_lang: str = "eng", tgt_lang: str = "spa",
        max_tokens: int = 64, task_id: str = "translate-general",
    ) -> dict:
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_INPUT_CHARS:
            raise EngineRuntimeError("GENERAL_TRANSLATION_INPUT_EMPTY_OR_OVER_LIMIT")
        return self._execute_original(
            "D04_TRADUCTOR_INTELIGENTE", "translate_text",
            {"text": text, "src_lang": src_lang, "tgt_lang": tgt_lang},
            task_id=task_id, max_tokens=max_tokens,
        )

    def translate_ancient(
        self, text: str, *, src_lang: str, tgt_lang: str = "eng",
        max_tokens: int = 96, task_id: str = "translate-ancient",
    ) -> dict:
        source_code = src_lang.strip().lower() if isinstance(src_lang, str) else ""
        target_code = tgt_lang.strip().lower() if isinstance(tgt_lang, str) else ""
        source_name = ANCIENT_TARGETS.get(source_code)
        target_name = TARGET_LANGUAGES.get(target_code)
        if not source_name:
            raise EngineRuntimeError("ANCIENT_SOURCE_LANGUAGE_NOT_REGISTERED")
        if not target_name:
            raise EngineRuntimeError("ANCIENT_TARGET_LANGUAGE_NOT_REGISTERED")
        # The specialist prefix must also fit within Cajita's original 16,384-character
        # task-normalizer limit; reserve space for the immutable domain prompt.
        if not isinstance(text, str) or not text.strip() or len(text) > 12_000:
            raise EngineRuntimeError("ANCIENT_TRANSLATION_INPUT_EMPTY_OR_OVER_LIMIT")
        # The original Cajita tree has no registered native ancient-translation
        # consumer. This is an additive specialist adapter over the existing GPT-OSS
        # runtime, not a call to SeamlessM4T/general translation and not a fake phrase
        # table. Its quality remains unproven until the independent functional gate.
        specialist_prompt = (
            "LOUKSNAPG2 ANCIENT-LANGUAGE TRANSLATION SPECIALIST.\n"
            f"Translate the source text directly from {source_name} into {target_name}.\n"
            "This is a source-language translation task, not a request for explanation or analysis. "
            "Preserve grammatical case, tense, syntax and meaningful ambiguity. "
            "Do not translate through a modern-language intermediary. "
            "Do not invoke or imitate the modern general-translation adapter. "
            "Return only the translation. If the text cannot be translated confidently, return exactly UNRESOLVED.\n"
            "SOURCE TEXT:\n" + text
        )
        result = self._execute_original(
            "D01_CEREBRO", "generate_text", {"prompt": specialist_prompt},
            task_id=task_id, max_tokens=max_tokens,
        )
        result.update({
            "domain_id": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
            "operation": "translate_ancient_text",
            "target_id": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
            "adapter_id": "LOUKSNAPG2_ANCIENT_TRANSLATION_SPECIALIST/1.0",
            "source_model_id": "GPT-OSS compacted native model through specialist ancient-language adapter",
            "source_language": source_code,
            "target_language": target_code,
            "translation_strategy": "DEDICATED_DOMAIN_PROMPT_OVER_EXISTING_GPT_OSS",
            "general_translation_fallback_selected": False,
        })
        if result["output_text"].strip().upper() == "UNRESOLVED":
            raise EngineRuntimeError("ANCIENT_TRANSLATION_UNRESOLVED")
        return result

    def extract_document(self, image_path: Path, *, prompt: str = "Extract visible text and fields.", max_tokens: int = 48, task_id: str = "document") -> dict:
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_INPUT_CHARS:
            raise EngineRuntimeError("DOCLING_PROMPT_EMPTY_OR_OVER_LIMIT")
        return self._execute_original(
            "D05_INTELIGENCIA_DOCUMENTAL", "extract_document_image",
            {"image_path": str(image_path), "prompt": prompt},
            task_id=task_id, max_tokens=max_tokens,
        )

    def transcribe(self, audio_path: Path, *, max_tokens: int = 64, task_id: str = "transcribe") -> dict:
        return self._execute_original(
            "D03_TRANSCRIPCION", "transcribe_audio", {"audio_path": str(audio_path)},
            task_id=task_id, max_tokens=max_tokens,
        )

    def route(self, domain_id: str, operation: str, payload: dict, *, task_id: str = "task") -> dict:
        if domain_id not in DOMAIN_IDS:
            raise EngineRuntimeError("DOMAIN_NOT_REGISTERED")
        if not isinstance(payload, dict):
            raise EngineRuntimeError("TASK_INPUT_NOT_OBJECT")
        max_tokens = payload.get("max_new_tokens", 64)
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= MAX_NEW_TOKENS:
            raise EngineRuntimeError("TOKEN_LIMIT_OUT_OF_RANGE")
        if domain_id == "D01_CEREBRO" and operation == "generate_text":
            return self.reason(payload.get("prompt", ""), max_tokens=max_tokens, task_id=task_id)
        if domain_id == "D06_SISTEMA_INTELIGENTE" and operation == "analyze_reasoning":
            return self.analyze(payload.get("prompt", ""), max_tokens=max_tokens, task_id=task_id)
        if domain_id == "D04_TRADUCTOR_INTELIGENTE" and operation == "translate_text":
            return self.translate_general(
                payload.get("text", ""), src_lang=payload.get("src_lang", "eng"),
                tgt_lang=payload.get("tgt_lang", "spa"), max_tokens=max_tokens, task_id=task_id,
            )
        if domain_id == "D04_TRADUCCION_LENGUAS_ANTIGUAS" and operation == "translate_ancient_text":
            return self.translate_ancient(
                payload.get("text", ""), src_lang=payload.get("src_lang", ""),
                tgt_lang=payload.get("tgt_lang", "eng"), max_tokens=max_tokens, task_id=task_id,
            )
        if domain_id == "D05_INTELIGENCIA_DOCUMENTAL" and operation == "extract_document_image":
            return self.extract_document(
                Path(payload.get("image_path", "")),
                prompt=payload.get("prompt", "Extract visible text and fields."),
                max_tokens=max_tokens, task_id=task_id,
            )
        if domain_id == "D03_TRANSCRIPCION" and operation == "transcribe_audio":
            return self.transcribe(Path(payload.get("audio_path", "")), max_tokens=max_tokens, task_id=task_id)
        raise EngineRuntimeError("DOMAIN_OPERATION_PAIR_NOT_REGISTERED")
