#!/usr/bin/env python3
"""Required target-side acceptance gate for the G06-derived Lunita beta overlay.

Must be invoked by the authorized CUSTOSZ_V7 worker after a verified checkpoint
and additive overlay receipt exist. A PASS is target-runtime evidence only;
it never issues S32, G23, G24, or canonical G06/G08 certification.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import pathlib
import subprocess
import sys
import time
import unittest
from datetime import datetime, timezone
from typing import Any

ROOT = pathlib.Path("/opt/lunita")
OVERLAY = ROOT / "engines/runtime_engines_v1"
STATE = pathlib.Path(os.environ.get("XDG_STATE_HOME") or (pathlib.Path.home() / ".local/state")) / "lunita"
REPORTS = STATE / "runtime_validation"
OVERLAY_RECEIPT = OVERLAY / "OVERLAY_APPLY_RECEIPT.json"
LEGACY_LAUNCHER = ROOT / "agent/lunita.py"
EXPECTED_LEGACY_SHA256 = "46efd711729c344e7efba9ce2503127c48f0b88207cc5a17311ff1d555b075b2"
LEGACY_SMOKE_COMMANDS = (
    "brujula-self-test",
    "r-self-test",
    "jamovi-self-test",
    "jasp-self-test",
    "fault",
)
TEST_MODULES = (
    "engine_acceptance_v1",
    "gateway_acceptance_v1",
    "launcher_acceptance_v1",
    "overlay_acceptance_v1",
)


class TargetGateError(RuntimeError):
    pass


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_directory(path: pathlib.Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_dir():
        raise TargetGateError(f"Required overlay directory is missing or symlinked: {path}")
    entries = []
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise TargetGateError(f"Symlink found in installed engine overlay: {item}")
        if item.is_file():
            entries.append({
                "path": item.relative_to(path).as_posix(),
                "sha256": sha256_file(item),
                "bytes": item.stat().st_size,
            })
        elif not item.is_dir():
            raise TargetGateError(f"Unexpected filesystem entry in overlay: {item}")
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "file_count": len(entries),
        "bytes": sum(entry["bytes"] for entry in entries),
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }


def verify_overlay() -> dict[str, Any]:
    if not OVERLAY_RECEIPT.is_file():
        raise TargetGateError("Additive overlay receipt is missing")
    receipt = json.loads(OVERLAY_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("schema") != "LUNITA_ADDITIVE_ENGINE_OVERLAY_RECEIPT/1.0":
        raise TargetGateError("Overlay receipt schema mismatch")
    if receipt.get("status") != "APPLIED_ADDITIVELY_NOT_CERTIFIED":
        raise TargetGateError("Overlay receipt status is not APPLIED_ADDITIVELY_NOT_CERTIFIED")
    if receipt.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1":
        raise TargetGateError("Overlay candidate identity mismatch")
    if receipt.get("worker_version") != "CUSTOSZ_V7":
        raise TargetGateError("Overlay receipt is not bound to CUSTOSZ_V7")
    if receipt.get("certification") != "NOT_GRANTED":
        raise TargetGateError("Unexpected inherited certification in additive overlay")
    if receipt.get("launcher_sha256") != EXPECTED_LEGACY_SHA256:
        raise TargetGateError("Legacy launcher digest in overlay receipt mismatch")
    observed_launcher = sha256_file(LEGACY_LAUNCHER)
    if observed_launcher != EXPECTED_LEGACY_SHA256:
        raise TargetGateError("Installed legacy launcher SHA-256 mismatch")
    for relative, expected in receipt.get("directories", {}).items():
        actual = hash_directory(OVERLAY / relative)
        if actual != expected:
            raise TargetGateError(f"Installed overlay directory hash mismatch: {relative}")
    return {
        "status": "PASS_OVERLAY_INTEGRITY",
        "receipt_sha256": sha256_file(OVERLAY_RECEIPT),
        "legacy_launcher_sha256": observed_launcher,
        "directory_integrity": "PASS",
        "frozen_g06_mutated": receipt.get("frozen_g06_mutated"),
        "canonical_g08_mutated": receipt.get("canonical_g08_mutated"),
    }


def run_unittests() -> dict[str, Any]:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for module_name in TEST_MODULES:
        module = importlib.import_module(module_name)
        suite.addTests(loader.loadTestsFromModule(module))
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    return {
        "status": "PASS" if result.wasSuccessful() and not result.skipped else "FAIL",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "failure_test_ids": [test.id() for test, _ in result.failures],
        "error_test_ids": [test.id() for test, _ in result.errors],
        "skipped_test_ids": [test.id() for test, _ in result.skipped],
    }


def run_qwen_via_v18() -> dict[str, Any]:
    model = ROOT / "brain/model/Qwen_Qwen3-0.6B-IQ3_XS.gguf"
    if not model.is_file():
        raise TargetGateError(f"Required Qwen model is missing: {model}")
    request = {
        "command": "/play PT",
        "agent": "Luna",
        "engine_id": "E01",
        "payload": {
            "prompt": "Responde únicamente OK.",
            "max_tokens": 4,
            "timeout_seconds": 120,
        },
    }
    temporary = STATE / "requests"
    temporary.mkdir(parents=True, exist_ok=True)
    request_path = temporary / f"e01-qwen-{time.time_ns()}.json"
    request_path.write_text(json.dumps(request, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join([
        str(OVERLAY / "vendor/python3.12/site-packages"),
        str(OVERLAY),
        environment.get("PYTHONPATH", ""),
    ]).rstrip(os.pathsep)
    environment["LUNITA_FASTEMBED_CACHE"] = str(OVERLAY / "model-cache/fastembed")
    environment["LUNITA_VECTOR_DB_PATH"] = str(STATE / "vectors")
    environment["LUNITA_ENGINE_AUDIT_LOG"] = str(STATE / "audit/engine-execution.jsonl")
    environment["HF_HUB_OFFLINE"] = "1"
    environment["TRANSFORMERS_OFFLINE"] = "1"
    environment["HF_HUB_DISABLE_TELEMETRY"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, str(OVERLAY / "lunita_beta_v1_8.py"),
             "engine-run", "--request", str(request_path)],
            env=environment, capture_output=True, text=True, timeout=150, check=False,
        )
    finally:
        request_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise TargetGateError("E01 Qwen inference failed: " + (proc.stderr or proc.stdout)[-2000:])
    result = json.loads(proc.stdout)
    if result.get("status") != "PASS_ENGINE_OPERATION" or result.get("engine_id") != "E01":
        raise TargetGateError("E01 gateway did not return PASS_ENGINE_OPERATION")
    if not result.get("audit_event_hash"):
        raise TargetGateError("E01 execution did not produce a provenance audit hash")
    payload = result.get("result", {})
    output = payload.get("output", "")
    if payload.get("returncode") != 0 or not output.strip():
        raise TargetGateError("Qwen returned no generated output")
    audit = pathlib.Path(environment["LUNITA_ENGINE_AUDIT_LOG"])
    if not audit.is_file():
        raise TargetGateError("Append-only engine audit log was not created")
    return {
        "status": "PASS_E01_QWEN_INFERENCE",
        "model": model.name,
        "model_sha256": sha256_file(model),
        "llama_cli_sha256": sha256_file(pathlib.Path(payload["runtime"])),
        "prompt_sha256": payload["prompt_sha256"],
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "audit_event_hash": result["audit_event_hash"],
        "audit_log_sha256": sha256_file(audit),
    }


def run_legacy_smokes() -> dict[str, Any]:
    import lunita_beta_v1_8 as launcher
    if launcher.sha256_file(LEGACY_LAUNCHER) != EXPECTED_LEGACY_SHA256:
        raise TargetGateError("Legacy launcher hash check failed before application smoke tests")
    results = {}
    for command in LEGACY_SMOKE_COMMANDS:
        rc = launcher.run_legacy([command])
        results[command] = {"returncode": rc, "status": "PASS" if rc == 0 else "FAIL"}
        if rc != 0:
            raise TargetGateError(f"Legacy application smoke test failed: {command} rc={rc}")
    return {"status": "PASS_LEGACY_APPLICATION_SMOKES", "commands": results}


def write_receipt(report: dict[str, Any]) -> pathlib.Path:
    REPORTS.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = REPORTS / f"LUNITA_TARGET_RUNTIME_ACCEPTANCE_{stamp}.json"
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("Short write while persisting target runtime receipt")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return path


def main() -> int:
    report: dict[str, Any] = {
        "schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_id": "G06_REBUILD_CANDIDATE_R1",
        "worker_required": "CUSTOSZ_V7",
        "target": str(ROOT),
        "status": "BLOCKED",
        "certification": "NOT_GRANTED",
        "canonical_g06_certification": "NOT_GRANTED",
        "canonical_g08_binding_mutation": False,
    }
    try:
        overlay = verify_overlay()
        import engine_runtime_v1 as engine
        registry = engine.validate_registry()
        dependencies = engine.engine_dependency_inventory()
        if dependencies["status"] != "PASS":
            raise TargetGateError("Runtime dependencies are missing: " + ", ".join(dependencies["missing"]))
        report["overlay_integrity"] = overlay
        report["engine_registry"] = registry
        report["dependency_inventory"] = dependencies
        report["qwen_e01"] = run_qwen_via_v18()
        report["engine_acceptance_tests"] = run_unittests()
        if report["engine_acceptance_tests"]["status"] != "PASS":
            raise TargetGateError("Engine acceptance suite failed or skipped tests")
        report["legacy_application_smokes"] = run_legacy_smokes()
        report["status"] = "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED"
    except Exception as exc:
        report["status"] = "BLOCKED_TARGET_RUNTIME_ACCEPTANCE"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)[:2400]}
    try:
        path = write_receipt(report)
        report["receipt_path"] = str(path)
        report["receipt_sha256"] = sha256_file(path)
    except Exception as exc:
        report["receipt_write_error"] = {"type": type(exc).__name__, "message": str(exc)[:1200]}
        report["status"] = "BLOCKED_TARGET_RUNTIME_ACCEPTANCE"
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
