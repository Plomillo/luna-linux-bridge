#!/usr/bin/env python3
"""LOUKSNAPG2 domain router over original Cajita models and bounded auxiliary engines.

Original model weights and native adapters remain source-bound and immutable.
The auxiliary engine is selected explicitly for supported operations; no route
labels auxiliary output as GPT-OSS, Qwen3, Seamless, Docling or Whisper-large output.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from louksnapg2_foma import FomaEngine, FomaRuntimeError
from louksnapg2_auxiliary import AuxiliaryEngineError, LouksnapG2AuxiliaryEngines, verify_whisper_auxiliary_assets

SCHEMA = "LOUKSNAPG2_ENGINE_RUNTIME/2.1"
CAJITA_TASK_SCHEMA = "CAJITA_TASK_REQUEST/1.0"
MAX_INPUT_CHARS = 16_384
MAX_NEW_TOKENS = 128
MAX_DOCLING_NEW_TOKENS = 256
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
        "source_model": "GPT-OSS compactado — rank-1 INT8 factors",
    },
    ("D06_SISTEMA_INTELIGENTE", "analyze_reasoning"): {
        "target_id": "D06_ANALISIS_AVANZADO",
        "adapter_id": "CAJITA_QWEN3_REASONING/1.0",
        "source_model": "Qwen3 compactado — low-rank INT8 factors",
    },
    ("D04_TRADUCTOR_INTELIGENTE", "translate_text"): {
        "target_id": "D04_TRADUCCION_GENERAL",
        "adapter_id": "CAJITA_SEAMLESS_TRANSLATION/1.0",
        "source_model": "SeamlessM4T v2 compactado — low-rank INT8 factors",
    },
    ("D05_INTELIGENCIA_DOCUMENTAL", "extract_document_image"): {
        "target_id": "D05_DOCLING",
        "adapter_id": "CAJITA_DOCLING_IMAGE_EXTRACTION/1.0",
        "source_model": "Granite Docling compactado — packed quantized weights",
    },
    ("D03_TRANSCRIPCION", "transcribe_audio"): {
        "target_id": "D03_TRANSCRIPCION_ROOT",
        "adapter_id": "CAJITA_WHISPER_TRANSCRIPTION/1.0",
        "source_model": "Whisper compactado — low-rank INT8 factors",
    },
}
AUXILIARY_ADAPTERS = {
    "D01_CEREBRO": "LOUKSNAPG2_FORMAL_REASONING_AUXILIARY/1.0",
    "D06_SISTEMA_INTELIGENTE": "LOUKSNAPG2_FORMAL_REASONING_AUXILIARY/1.0",
    "D04_TRADUCTOR_INTELIGENTE": "LOUKSNAPG2_APERTIUM_TRANSLATION_AUXILIARY/1.0",
    "D05_INTELIGENCIA_DOCUMENTAL": "LOUKSNAPG2_TESSERACT_OCR_AUXILIARY/1.0",
    "D03_TRANSCRIPCION": "LOUKSNAPG2_WHISPER_CPP_AUXILIARY/1.0",
}


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
    """Governed route between immutable source adapters and explicitly named auxiliary engines."""

    def __init__(self, root: Path, threads: int = 1):
        if isinstance(threads, bool) or threads != 1:
            raise EngineRuntimeError("CPU_THREAD_BUDGET_MUST_BE_ONE")
        self.root = _cajita_root(Path(root))
        self.threads = 1
        self._adapter_module = None
        self._model_evidence = None
        self._foma = FomaEngine(self.root)
        self._auxiliary = LouksnapG2AuxiliaryEngines(self.root)

    def _auxiliary_preflight(self) -> dict:
        runtime = self.root / "LOUKSNAPG2_RUNTIME"
        formal = {
            "status": "LIMITED_SCOPE",
            "engine_id": "LOUKSNAPG2_FORMAL_REASONING/1.0",
            "scope": "SAFE_ARITHMETIC_AND_SUPPORTED_SYLLOGISTIC_PATTERNS",
            "unsupported_prompt_policy": "FAIL_CLOSED_NO_DEGRADED_NEURAL_FALLBACK",
        }
        translation = {"status": "AVAILABLE" if shutil.which("apertium") else "NOT_PROVISIONED",
                       "engine_id": "APERTIUM_LOCAL_BILINGUAL_PIPELINE/1.0",
                       "required_pairs": ["eng-spa", "spa-eng", "fra-spa", "spa-fra"]}
        document = {"status": "AVAILABLE" if shutil.which("tesseract") else "NOT_PROVISIONED",
                    "engine_id": "TESSERACT_OCR/5.x"}
        try:
            whisper = verify_whisper_auxiliary_assets(runtime)
            whisper = {
                **whisper,
                "engine_id": "WHISPER_CPP_TINY_MULTILINGUAL/1.9.5",
                "host": "linux-x86_64",
            }
        except AuxiliaryEngineError as exc:
            message = str(exc)
            whisper = {
                "status": "NOT_PROVISIONED" if "ASSET_MISSING" in message else "FAIL_IDENTITY",
                "engine_id": "WHISPER_CPP_TINY_MULTILINGUAL/1.9.5",
                "reason": message[:300],
                "host": "linux-x86_64",
            }
        return {
            "formal_reasoning": formal,
            "translation": translation,
            "document_ocr": document,
            "transcription": whisper,
        }

    def preflight(self) -> dict:
        evidence = verify_model_files(self.root)
        manifest = self.root / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
        if manifest.is_symlink() or not manifest.is_file():
            raise EngineRuntimeError("ORIGINAL_MODEL_WEIGHT_MANIFEST_MISSING")
        self._model_evidence = evidence
        ancient = self._foma.preflight()
        return {
            "schema": "LOUKSNAPG2_RUNTIME_PREFLIGHT/2.1",
            "status": "PASS_MODEL_SOURCE_IDENTITIES",
            "thread_count": self.threads,
            "source_model_policy": "ORIGINAL_MODEL_WEIGHTS_IMMUTABLE; AUXILIARY_BACKENDS_SEPARATELY_IDENTIFIED",
            "new_external_model_fetch_performed": False,
            "models": evidence,
            "auxiliary_engines": self._auxiliary_preflight(),
            "required_domains": {
                "D01_CEREBRO": "Original GPT-OSS retained; bounded formal arithmetic backend handles supported expressions",
                "D06_SISTEMA_INTELIGENTE": "Original Qwen3 retained; bounded formal inference backend handles supported syllogisms",
                "D04_TRADUCTOR_INTELIGENTE": "Apertium local bilingual runtime (eng-spa; fra-spa via Spanish pivot)",
                "D05_INTELIGENCIA_DOCUMENTAL": "Tesseract local OCR; original Docling weights retained and not relabelled",
                "D04_TRADUCCION_LENGUAS_ANTIGUAS": "Foma finite-state transducer; hash-pinned linguistic transducers required",
                "D03_TRANSCRIPCION": "whisper.cpp tiny multilingual auxiliary ASR; original Whisper weights retained",
            },
            "ancient_translation": ancient,
            "general_translation_fallback_for_ancient": False,
            "certification": "NOT_GRANTED_BY_PREFLIGHT",
        }

    def _auxiliary_result(self, domain_id: str, operation: str, result: dict, *, task_id: str) -> dict:
        route = NATIVE_ROUTES.get((domain_id, operation))
        if route is None:
            raise EngineRuntimeError("AUXILIARY_DOMAIN_OPERATION_PAIR_NOT_REGISTERED")
        output = result.get("output_text")
        if not isinstance(output, str) or not output.strip():
            raise EngineRuntimeError("AUXILIARY_ENGINE_OUTPUT_EMPTY")
        if self._model_evidence is None:
            self._model_evidence = verify_model_files(self.root)
        tokens = len(output.split())
        return {
            "schema": "LOUKSNAPG2_TASK_RESULT/2.1",
            "status": "PASS_EXECUTION",
            "execution_authorized": True,
            "task_id": task_id,
            "domain_id": domain_id,
            "operation": operation,
            "target_id": route["target_id"],
            "adapter_id": AUXILIARY_ADAPTERS[domain_id],
            "output_text": output,
            "output_sha256": sha256_bytes(output.encode("utf-8")),
            "model_source_evidence": self._model_evidence.get(domain_id, {}),
            "source_model_id": result.get("engine_id"),
            "source_runtime_status": "PASS_AUXILIARY_ENGINE_EXECUTION",
            "generated_token_count": tokens,
            "auxiliary_engine_evidence": {k: v for k, v in result.items() if k != "output_text"},
            "translation_strategy": result.get("translation_route"),
            "source_language": result.get("source_language"),
            "target_language": result.get("target_language"),
            "general_translation_fallback_selected": False,
            "neural_model_equivalence": "NOT_ESTABLISHED",
            "original_neural_model_execution": "NOT_USED_FOR_THIS_TASK",
            "certification": "NOT_GRANTED_BY_RUNTIME_CALL",
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
            if os.environ.get("CAJITA_E2E_DIAGNOSTICS") == "1":
                details = []
                for key in ("return_code", "peak_rss_bytes", "resource_policy", "diagnostic_stderr_tail", "diagnostic_stdout_tail"):
                    value = result.get(key)
                    if value is not None and (not isinstance(value, str) or value.strip()):
                        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
                        details.append(key + "=" + rendered[-800:])
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
        try:
            result = self._auxiliary.reasoning(prompt)
        except AuxiliaryEngineError as exc:
            raise EngineRuntimeError("FORMAL_REASONING_AUXILIARY_FAILED:" + str(exc)[:300]) from exc
        if result is None:
            raise EngineRuntimeError("FORMAL_REASONING_SCOPE_UNSUPPORTED_NO_NEURAL_FALLBACK")
        return self._auxiliary_result("D01_CEREBRO", "generate_text", result, task_id=task_id)

    def analyze(self, prompt: str, *, max_tokens: int = 64, task_id: str = "analysis") -> dict:
        try:
            result = self._auxiliary.reasoning(prompt)
        except AuxiliaryEngineError as exc:
            raise EngineRuntimeError("FORMAL_REASONING_AUXILIARY_FAILED:" + str(exc)[:300]) from exc
        if result is None:
            raise EngineRuntimeError("FORMAL_REASONING_SCOPE_UNSUPPORTED_NO_NEURAL_FALLBACK")
        return self._auxiliary_result("D06_SISTEMA_INTELIGENTE", "analyze_reasoning", result, task_id=task_id)

    def translate_general(
        self, text: str, *, src_lang: str = "eng", tgt_lang: str = "spa",
        max_tokens: int = 64, task_id: str = "translate-general",
    ) -> dict:
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_INPUT_CHARS:
            raise EngineRuntimeError("GENERAL_TRANSLATION_INPUT_EMPTY_OR_OVER_LIMIT")
        try:
            result = self._auxiliary.translate(text, src_lang, tgt_lang)
        except AuxiliaryEngineError as exc:
            raise EngineRuntimeError("APERTIUM_AUXILIARY_TRANSLATION_FAILED:" + str(exc)[:400]) from exc
        return self._auxiliary_result("D04_TRADUCTOR_INTELIGENTE", "translate_text", result, task_id=task_id)

    def translate_ancient(
        self, text: str, *, src_lang: str, tgt_lang: str = "eng",
        max_tokens: int = 96, task_id: str = "translate-ancient",
    ) -> dict:
        source_code = src_lang.strip().lower() if isinstance(src_lang, str) else ""
        target_code = tgt_lang.strip().lower() if isinstance(tgt_lang, str) else ""
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_INPUT_CHARS:
            raise EngineRuntimeError("ANCIENT_TRANSLATION_INPUT_EMPTY_OR_OVER_LIMIT")
        try:
            result = self._foma.translate(text, src_lang=source_code, tgt_lang=target_code)
        except FomaRuntimeError as exc:
            raise EngineRuntimeError(str(exc)) from exc
        result.update({
            "task_id": task_id,
            "source_model_id": "Foma finite-state engine with source-pinned linguistic transducer",
            "semantic_quality_equivalence_to_full_size_original": "NOT_ESTABLISHED",
        })
        return result

    def extract_document(self, image_path: Path, *, prompt: str = "Extract visible text and fields.", max_tokens: int = 48, task_id: str = "document") -> dict:
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_INPUT_CHARS:
            raise EngineRuntimeError("DOCLING_PROMPT_EMPTY_OR_OVER_LIMIT")
        try:
            result = self._auxiliary.extract_document(image_path)
        except AuxiliaryEngineError as exc:
            raise EngineRuntimeError("TESSERACT_OCR_AUXILIARY_FAILED:" + str(exc)[:400]) from exc
        return self._auxiliary_result("D05_INTELIGENCIA_DOCUMENTAL", "extract_document_image", result, task_id=task_id)

    def transcribe(self, audio_path: Path, *, max_tokens: int = 64, task_id: str = "transcribe") -> dict:
        try:
            result = self._auxiliary.transcribe(audio_path)
        except AuxiliaryEngineError as exc:
            raise EngineRuntimeError("WHISPER_CPP_AUXILIARY_FAILED:" + str(exc)[:400]) from exc
        return self._auxiliary_result("D03_TRANSCRIPCION", "transcribe_audio", result, task_id=task_id)

    def route(self, domain_id: str, operation: str, payload: dict, *, task_id: str = "task") -> dict:
        if domain_id not in DOMAIN_IDS:
            raise EngineRuntimeError("DOMAIN_NOT_REGISTERED")
        if not isinstance(payload, dict):
            raise EngineRuntimeError("TASK_INPUT_NOT_OBJECT")
        max_tokens = payload.get("max_new_tokens", 64)
        token_ceiling = MAX_DOCLING_NEW_TOKENS if domain_id == "D05_INTELIGENCIA_DOCUMENTAL" else MAX_NEW_TOKENS
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= token_ceiling:
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
