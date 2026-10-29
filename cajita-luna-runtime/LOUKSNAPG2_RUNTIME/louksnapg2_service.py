#!/usr/bin/env python3
"""LOUKSNAPG2 public task entrypoint and strict domain-to-engine bridge.

The original Cajita runtime and router remain byte-for-byte unchanged. This additive
entrypoint maps canonical target IDs onto the new externalized model runtime with
a closed target/operation table. Unknown targets, mismatches and undocumented
operations fail closed; ancient-language tasks can never fall back to general
translation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from louksnapg2_engine import EngineRuntimeError, LouksnapG2Runtime

SCHEMA_REQUEST = "LOUKSNAPG2_DOMAIN_TASK_REQUEST/1.0"
SCHEMA_RESULT = "LOUKSNAPG2_DOMAIN_TASK_RESULT/1.0"
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

TARGET_BINDINGS: dict[str, dict[str, str]] = {
    "D01_CEREBRO_ROOT": {
        "domain_id": "D01_CEREBRO",
        "operation": "generate_text",
        "adapter_id": "LOUKSNAPG2_CEREBRO_ADAPTER/1.0",
    },
    "D06_ANALISIS_AVANZADO": {
        "domain_id": "D06_SISTEMA_INTELIGENTE",
        "operation": "analyze_reasoning",
        "adapter_id": "LOUKSNAPG2_QWEN_ANALYSIS_ADAPTER/1.0",
    },
    "D04_TRADUCCION_GENERAL": {
        "domain_id": "D04_TRADUCTOR_INTELIGENTE",
        "operation": "translate_text",
        "adapter_id": "LOUKSNAPG2_GENERAL_TRANSLATION_ADAPTER/1.0",
    },
    "D04_TRADUCCION_LENGUAS_ANTIGUAS": {
        "domain_id": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
        "operation": "translate_ancient_text",
        "adapter_id": "LOUKSNAPG2_ANCIENT_TRANSLATION_ADAPTER/1.0",
    },
    "D03_TRANSCRIPCION_ROOT": {
        "domain_id": "D03_TRANSCRIPCION",
        "operation": "transcribe_audio",
        "adapter_id": "LOUKSNAPG2_WHISPER_TRANSCRIPTION_ADAPTER/1.0",
    },
}


class ServiceError(RuntimeError):
    pass


def sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def dispatch_target(runtime: LouksnapG2Runtime, target_id: str, payload: dict[str, Any], *, task_id: str) -> dict:
    if not isinstance(task_id, str) or TASK_ID_RE.fullmatch(task_id) is None:
        raise ServiceError("TASK_ID_INVALID")
    binding = TARGET_BINDINGS.get(target_id)
    if not binding:
        raise ServiceError("TARGET_NOT_REGISTERED:" + str(target_id))
    if not isinstance(payload, dict):
        raise ServiceError("TASK_PAYLOAD_NOT_OBJECT")
    domain_id = binding["domain_id"]
    operation = binding["operation"]
    result = runtime.route(domain_id, operation, payload)
    if result.get("status") != "PASS_EXECUTION" or result.get("execution_authorized") is not True:
        raise ServiceError("ENGINE_RESULT_NOT_EXECUTED")
    if result.get("domain_id") != domain_id or result.get("operation") != operation:
        raise ServiceError("ENGINE_ROUTE_RESULT_BINDING_MISMATCH")
    fallback = result.get("general_translation_fallback_selected", False)
    if target_id == "D04_TRADUCCION_LENGUAS_ANTIGUAS" and fallback is not False:
        raise ServiceError("ANCIENT_TRANSLATION_FALLBACK_FORBIDDEN")
    return {
        "schema": SCHEMA_RESULT,
        "status": "PASS_EXECUTION",
        "task_id": task_id,
        "target_id": target_id,
        "domain_id": domain_id,
        "operation": operation,
        "adapter_id": binding["adapter_id"],
        "request_sha256": sha256_json(payload),
        "output_text": result.get("output_text"),
        "output_sha256": result.get("output_sha256"),
        "source_model_evidence": result.get("model_source_evidence", {}),
        "translation_strategy": result.get("translation_strategy"),
        "source_language": result.get("source_language"),
        "target_language": result.get("target_language"),
        "general_translation_fallback_selected": False if target_id.startswith("D04_TRADUCCION_") else fallback,
        "quality": "EVALUATED_ONLY_BY_SEPARATE_FUNCTIONAL_GATE",
        "certification": "NOT_GRANTED_BY_DISPATCH",
    }


def execute_request(runtime: LouksnapG2Runtime, request: dict[str, Any]) -> dict:
    if not isinstance(request, dict) or request.get("schema") != SCHEMA_REQUEST:
        raise ServiceError("REQUEST_SCHEMA_MISMATCH")
    task_id = request.get("task_id")
    target_id = request.get("target_id")
    payload = request.get("payload")
    if not isinstance(target_id, str) or not isinstance(payload, dict):
        raise ServiceError("REQUEST_TARGET_OR_PAYLOAD_INVALID")
    binding = TARGET_BINDINGS.get(target_id)
    if not binding:
        raise ServiceError("TARGET_NOT_REGISTERED:" + target_id)
    supplied_domain = request.get("domain_id")
    supplied_operation = request.get("operation")
    if supplied_domain is not None and supplied_domain != binding["domain_id"]:
        raise ServiceError("REQUEST_DOMAIN_BINDING_MISMATCH")
    if supplied_operation is not None and supplied_operation != binding["operation"]:
        raise ServiceError("REQUEST_OPERATION_BINDING_MISMATCH")
    return dispatch_target(runtime, target_id, payload, task_id=task_id)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=Path(__file__).resolve().parent)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    execute = sub.add_parser("execute")
    execute.add_argument("--request-json", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        runtime = LouksnapG2Runtime(args.runtime_root.resolve(strict=True), threads=1)
        if args.command == "preflight":
            result = runtime.preflight()
        else:
            request_path = args.request_json
            if request_path.is_symlink() or not request_path.is_file():
                raise ServiceError("REQUEST_FILE_MISSING_OR_UNSAFE")
            request = json.loads(request_path.read_text(encoding="utf-8"))
            result = execute_request(runtime, request)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({
            "schema": SCHEMA_RESULT,
            "status": "FAIL_CLOSED",
            "execution_authorized": False,
            "reason": type(exc).__name__ + ":" + str(exc)[:300],
            "general_translation_fallback_selected": False,
            "certification": "NOT_GRANTED",
        }, ensure_ascii=False, sort_keys=True))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
