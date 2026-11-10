#!/usr/bin/env python3
"""Required target-side acceptance gate for the G06-derived Lunita beta overlay.

Run after a verified checkpoint and additive overlay receipt exist. A PASS is target-runtime evidence only;
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
import tempfile
import unittest
from datetime import datetime, timezone
from typing import Any

ROOT = pathlib.Path(os.environ.get("LUNITA_ROOT", "/opt/lunita")).expanduser()
OVERLAY = ROOT / "engines/runtime_engines_v1"
STATE = pathlib.Path(os.environ.get("XDG_STATE_HOME") or (pathlib.Path.home() / ".local/state")) / "lunita"
REPORTS = pathlib.Path(os.environ.get("LUNITA_TARGET_RUNTIME_RECEIPT_DIR", str(STATE / "runtime_validation"))).expanduser()
OVERLAY_RECEIPT = OVERLAY / "OVERLAY_APPLY_RECEIPT.json"
LEGACY_LAUNCHER = ROOT / "agent/lunita.py"
EXPECTED_LEGACY_SHA256 = "46efd711729c344e7efba9ce2503127c48f0b88207cc5a17311ff1d555b075b2"
LEGACY_SMOKE_COMMANDS = (
    ("brujula-self-test",),
    ("r-self-test",),
    ("jamovi-self-test",),
    ("jasp-self-test",),
    ("fault", "model-missing"),
    ("fault", "model-corrupted"),
    ("fault", "dependency-missing"),
    ("fault", "permission-denied"),
    ("fault", "low-memory"),
    ("fault", "process-crash"),
    ("fault", "browser-crash"),
    ("fault", "tool-failure"),
    ("fault", "invalid-input"),
    ("fault", "interrupted-execution"),
    ("fault", "restart"),
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


def verify_rootfs_build_receipt() -> dict[str, Any]:
    """Verify the reconstructed rootfs provenance and every declared major runtime payload."""
    path = ROOT / "metadata/ROOTFS_BUILD_RECEIPT.json"
    if path.is_symlink() or not path.is_file():
        raise TargetGateError("Rootfs build receipt is missing or not a regular file")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "LUNITA_ROOTFS_BUILD_RECEIPT/1.0":
        raise TargetGateError("Rootfs build receipt schema mismatch")
    if receipt.get("status") != "PASS_ROOTFS_BUILD_NOT_CERTIFIED":
        raise TargetGateError("Rootfs builder did not report an accepted build")
    if receipt.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1":
        raise TargetGateError("Rootfs build candidate identity mismatch")
    if receipt.get("source_rootfs_recovered") is not False:
        raise TargetGateError("Rebuilt rootfs provenance is ambiguous")
    ubuntu = receipt.get("ubuntu", {})
    if ubuntu.get("release") != "24.04" or ubuntu.get("codename") != "noble" or ubuntu.get("architecture") != "amd64":
        raise TargetGateError("Rootfs is not the registered Ubuntu 24.04 amd64 baseline")

    def require_hash(relative: str, expected: str, label: str) -> pathlib.Path:
        target = pathlib.Path(relative)
        if target.is_absolute():
            full = target
        else:
            full = ROOT / target
        if full.is_symlink() or not full.is_file():
            raise TargetGateError(f"Required rootfs payload is missing: {label}")
        observed = sha256_file(full)
        if not isinstance(expected, str) or observed != expected:
            raise TargetGateError(f"Rootfs payload digest mismatch: {label}")
        return full

    launcher = receipt.get("legacy_launcher", {})
    require_hash("agent/lunita.py", launcher.get("sha256"), "legacy beta-v1.7 launcher")
    qwen = receipt.get("qwen", {})
    if qwen.get("quantization") != "IQ3_XS" or qwen.get("revision") != "f9184d8b4c371cb52af5b8cb3d38e55e3cf0f4a0":
        raise TargetGateError("Qwen model source identity or quantization is not pinned")
    model = require_hash("brain/model/Qwen_Qwen3-0.6B-IQ3_XS.gguf", qwen.get("sha256"), "Qwen3 IQ3_XS model")
    if model.stat().st_size != qwen.get("bytes"):
        raise TargetGateError("Qwen model byte count differs from the build receipt")

    llama = receipt.get("llama_cpp", {})
    if llama.get("commit") != "cd959bae99ff4bed22bef2604f45241c09bbb8c8":
        raise TargetGateError("llama.cpp source commit is not pinned to the registered release")
    llama_candidates = list((ROOT / "brain/runtime").rglob("llama-cli"))
    if len(llama_candidates) != 1:
        raise TargetGateError(f"Expected exactly one packaged llama-cli, found {len(llama_candidates)}")
    require_hash(str(llama_candidates[0]), llama.get("llama_cli_sha256"), "llama.cpp llama-cli")

    brujula = receipt.get("brujula", {})
    if brujula.get("node") != "v22.23.2" or brujula.get("playwright") != "1.63.0" or brujula.get("playwright_core") != "1.63.0":
        raise TargetGateError("Brújula Node/Playwright versions do not match the registered runtime")
    browser_root = ROOT / "instruments/brujula"
    require_hash("instruments/brujula/node/bin/node", brujula.get("node_binary_sha256"), "Node.js binary")
    require_hash("instruments/brujula/chrome/chrome", brujula.get("chrome_binary_sha256"), "Chrome for Testing binary")
    for package in ("playwright", "playwright-core"):
        metadata = browser_root / "node_modules" / package / "package.json"
        if metadata.is_symlink() or not metadata.is_file():
            raise TargetGateError(f"Brújula package is missing: {package}")
        if json.loads(metadata.read_text(encoding="utf-8")).get("version") != "1.63.0":
            raise TargetGateError(f"Brújula package version mismatch: {package}")
    target_rootfs = ROOT.parents[1]
    guest_node = "/opt/lunita/instruments/brujula/node/bin/node"
    guest_chrome = "/opt/lunita/instruments/brujula/chrome/chrome"
    node_result = subprocess.run(
        ["chroot", str(target_rootfs), "/usr/bin/env", "-C", "/tmp", guest_node, "--version"],
        capture_output=True, text=True, check=False,
    )
    if node_result.returncode != 0 or node_result.stdout.strip() != "v22.23.2":
        raise TargetGateError("Node.js target-rootfs runtime did not return the pinned version")
    chrome_result = subprocess.run(
        ["chroot", str(target_rootfs), "/usr/bin/env", "-C", "/tmp", guest_chrome, "--version"],
        capture_output=True, text=True, check=False,
    )
    if chrome_result.returncode != 0 or "153.0.8010.12" not in chrome_result.stdout:
        raise TargetGateError("Chrome for Testing target-rootfs executable did not return the pinned version")

    lapiz = receipt.get("lapiz", {})
    if lapiz.get("r_version") != "4.6.1":
        raise TargetGateError("Lápiz R version is not pinned to 4.6.1")
    rscript = require_hash("instruments/lapiz/R-4.6.1/bin/Rscript", lapiz.get("rscript_sha256"), "Rscript binary")
    r_home = "/opt/lunita/instruments/lapiz/R-4.6.1/lib/R"
    r = subprocess.run(
        [
            "chroot", str(target_rootfs), "/usr/bin/env", "-C", "/tmp",
            f"R_HOME={r_home}",
            "/opt/lunita/instruments/lapiz/R-4.6.1/bin/Rscript",
            "-e", 'stopifnot(as.character(getRversion())=="4.6.1", 2+2==4)',
        ],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        raise TargetGateError("Lápiz R 4.6.1 execution failed: " + (r.stderr or r.stdout)[-1200:])

    apps = (
        ("org.jamovi.jamovi", "sacapuntas", "2.7.27"),
        ("org.jaspstats.JASP", "lupa", "0.98.1"),
    )
    observed_apps = {}
    for app_id, key, expected_version in apps:
        value = receipt.get(key, {})
        if value.get("application_id") != app_id or value.get("version") != expected_version:
            raise TargetGateError(f"Flatpak app identity/version mismatch: {app_id}")
        if not (pathlib.Path(os.environ.get("FLATPAK_SYSTEM_DIR", "/var/lib/flatpak")) / "app" / app_id).is_dir():
            raise TargetGateError(f"Flatpak system deployment is missing: {app_id}")
        if value.get("version_source") != "EXACT_PINNED_FLATPAK_COMMIT_MAPPING":
            raise TargetGateError(f"Flatpak version is not bound to its recorded commit mapping: {app_id}")
        info = subprocess.run(
            ["/usr/bin/flatpak", "info", "--system", "--show-commit", app_id],
            capture_output=True, text=True, check=False,
        )
        if info.returncode != 0:
            raise TargetGateError(f"Flatpak could not inspect the target system app: {app_id}")
        if info.stdout.strip() != value.get("flatpak_commit"):
            raise TargetGateError(f"Flatpak installed commit mismatch: {app_id}")
        observed_apps[app_id] = {
            "version": expected_version,
            "version_source": value.get("version_source"),
            "commit": info.stdout.strip(),
        }

    invariants = receipt.get("invariants", {})
    if any(invariants.get(flag) is not False for flag in (
        "frozen_g06_mutated", "canonical_g08_mutated", "legacy_launcher_replaced",
        "canonical_certification_inherited",
    )):
        raise TargetGateError("Rootfs build receipt does not preserve frozen/canonical identity")

    return {
        "status": "PASS_ROOTFS_BUILD_IDENTITY",
        "receipt_sha256": sha256_file(path),
        "source_rootfs_recovered": False,
        "ubuntu": ubuntu,
        "qwen_model_sha256": sha256_file(model),
        "llama_cli_sha256": sha256_file(llama_candidates[0]),
        "node_version": brujula.get("node"),
        "playwright_version": brujula.get("playwright"),
        "chrome_version": brujula.get("chrome_for_testing"),
        "r_version": lapiz.get("r_version"),
        "flatpak_apps": observed_apps,
        "certification": "NOT_GRANTED",
    }


def verify_e04_quantization_receipt() -> dict[str, Any]:
    cache = OVERLAY / "model-cache/fastembed"
    receipt_path = cache / "LUNITA_E04_ONNX_QUANTIZATION_RECEIPT.json"
    relative_model = pathlib.Path(
        "models--Qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q/"
        "snapshots/faf4aa4225822f3bc6376869cb1164e8e3feedd0/model_optimized.onnx"
    )
    model_path = cache / relative_model
    if receipt_path.is_symlink() or model_path.is_symlink() or not receipt_path.is_file() or not model_path.is_file():
        raise TargetGateError("Measured INT8 E04 model or regular quantization receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS_INT8_QUANTIZATION_MEASURED":
        raise TargetGateError("E04 quantization receipt is not a measured PASS")
    if receipt.get("model_id") != "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2":
        raise TargetGateError("E04 model identity mismatch")
    if receipt.get("model_cache_relative_path") != relative_model.as_posix():
        raise TargetGateError("E04 model snapshot path is not the registered pinned snapshot")
    if receipt.get("embedding_dimension") != 384:
        raise TargetGateError("E04 embedding dimension mismatch")
    if receipt.get("quantization") != "ONNX_RUNTIME_DYNAMIC_QINT8_PER_CHANNEL":
        raise TargetGateError("Unexpected E04 quantization method")
    if sha256_file(model_path) != receipt.get("quantized_sha256"):
        raise TargetGateError("E04 ONNX quantized model digest mismatch")
    validation = receipt.get("onnx_validation", {})
    if validation.get("onnxruntime_load_status") != "PASS":
        raise TargetGateError("ONNX Runtime did not load the quantized model")
    if not isinstance(validation.get("int8_initializer_count"), int) or validation["int8_initializer_count"] < 1:
        raise TargetGateError("INT8 model contains no measured quantized weight initializers")
    if not validation.get("quantized_operator_counts"):
        raise TargetGateError("INT8 model contains no quantized ONNX operators")
    if validation.get("checker_status") not in {
        "PASS_ONNX_CHECKER",
        "KNOWN_ONNX_SCHEMA_REGISTRY_GAP_LAYER_NORMALIZATION_OPSET11",
    }:
        raise TargetGateError("Unsupported ONNX graph validation status")
    thresholds = receipt.get("thresholds", {})
    mean_min = thresholds.get("minimum_mean_vector_cosine")
    vector_min = thresholds.get("minimum_vector_cosine")
    retrieval_required = thresholds.get("required_retrieval_top1_agreement")
    size_max = thresholds.get("maximum_model_size_ratio")
    if not isinstance(mean_min, (int, float)) or receipt.get("mean_vector_cosine", 0) < mean_min:
        raise TargetGateError("E04 mean vector cosine fell below the measured threshold")
    if not isinstance(vector_min, (int, float)) or receipt.get("minimum_vector_cosine", 0) < vector_min:
        raise TargetGateError("E04 minimum vector cosine fell below the measured threshold")
    if receipt.get("retrieval_top1_agreement") != retrieval_required:
        raise TargetGateError("E04 retrieval top-1 agreement did not meet the registered threshold")
    if not isinstance(size_max, (int, float)) or receipt.get("size_ratio", 1) >= size_max:
        raise TargetGateError("E04 INT8 model did not meet the registered size-reduction threshold")
    if receipt.get("quantized_bytes") != model_path.stat().st_size or receipt.get("original_bytes", 0) <= 0:
        raise TargetGateError("E04 quantized model size is not bound to the receipt")
    observed_ratio = receipt["quantized_bytes"] / receipt["original_bytes"]
    if abs(observed_ratio - receipt.get("size_ratio", -1)) > 1e-9:
        raise TargetGateError("E04 quantized model size ratio does not match its byte counts")
    decisions = receipt.get("retrieval_decisions", [])
    if len(decisions) != receipt.get("query_count") or len(decisions) != 10:
        raise TargetGateError("E04 retrieval evidence is incomplete")
    if not all(item.get("top1_match") for item in decisions):
        raise TargetGateError("E04 retrieval corpus contains a top-1 regression")
    return {
        "status": "PASS_E04_INT8_QUALITY_GATE",
        "receipt_sha256": sha256_file(receipt_path),
        "model_sha256": sha256_file(model_path),
        "onnx_validation": validation,
        "mean_vector_cosine": receipt["mean_vector_cosine"],
        "minimum_vector_cosine": receipt["minimum_vector_cosine"],
        "retrieval_top1_agreement": receipt["retrieval_top1_agreement"],
        "size_ratio": receipt["size_ratio"],
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
    if receipt.get("certification") != "NOT_GRANTED":
        raise TargetGateError("Unexpected inherited certification in additive overlay")
    if receipt.get("launcher_sha256") != EXPECTED_LEGACY_SHA256:
        raise TargetGateError("Legacy launcher digest in overlay receipt mismatch")
    observed_launcher = sha256_file(LEGACY_LAUNCHER)
    if observed_launcher != EXPECTED_LEGACY_SHA256:
        raise TargetGateError("Installed legacy launcher SHA-256 mismatch")
    required_files = {
        "__init__.py", "engine_runtime_v1.py", "engine_acceptance_v1.py",
        "engine_gateway_v1.py", "gateway_acceptance_v1.py", "lunita_beta_v1_8.py",
        "launcher_acceptance_v1.py", "target_runtime_acceptance_v1.py",
        "apply_engine_overlay_v1.py", "checkpoint_v1.py", "overlay_acceptance_v1.py",
        "engine_assignments_v1.json", "requirements-engine-stack.txt",
        "DEPENDENCY_EVIDENCE_v1.json", "ENGINE_RUNTIME_V1_README.md",
    }
    files = receipt.get("files")
    if not isinstance(files, dict) or set(files) != required_files:
        raise TargetGateError("Overlay file manifest is incomplete or contains unexpected entries")
    for relative, expected in files.items():
        path = OVERLAY / relative
        if path.is_symlink() or not path.is_file() or sha256_file(path) != expected:
            raise TargetGateError(f"Installed overlay file hash mismatch: {relative}")
    required_directories = {"vendor/python3.12/site-packages", "model-cache/fastembed"}
    directories = receipt.get("directories")
    if not isinstance(directories, dict) or set(directories) != required_directories:
        raise TargetGateError("Overlay directory manifest is incomplete or unexpected")
    for relative, expected in directories.items():
        actual = hash_directory(OVERLAY / relative)
        if actual != expected:
            raise TargetGateError(f"Installed overlay directory hash mismatch: {relative}")
    immutable_flags = (
        "canonical_identity_mutation", "engine_reassignment", "command_reassignment",
        "agent_reassignment", "frozen_g06_mutated", "canonical_g08_mutated",
        "launcher_mutated", "model_weights_mutated",
    )
    if any(receipt.get(flag) is not False for flag in immutable_flags):
        raise TargetGateError("Overlay receipt does not prove all frozen identity and artifact invariants")
    return {
        "status": "PASS_OVERLAY_INTEGRITY",
        "receipt_sha256": sha256_file(OVERLAY_RECEIPT),
        "legacy_launcher_sha256": observed_launcher,
        "directory_integrity": "PASS",
        "frozen_g06_mutated": receipt.get("frozen_g06_mutated"),
        "canonical_g08_mutated": receipt.get("canonical_g08_mutated"),
    }


REQUIRED_ENGINE_TEST_MATCHERS = {
    "E02": "test_e02_spanish_nlp_executes_pipeline",
    "E03": "test_e03_rag_returns_source_bound_context",
    "E04": "test_e04_embedding_and_e05_vector_search_execute_real_models",
    "E05": "test_e04_embedding_and_e05_vector_search_execute_real_models",
    "E06": "test_e06_knowledge_graph_executes_paths",
    "E07": "test_e07_rdf_parse_serialize_and_sparql",
    "E08": "test_e08_owl_profile_validates_explicit_classes_and_properties",
    "E09": "test_e09_owlrl_semantic_inference_materializes_subclass_entailment",
    "E10": "test_e10_safe_rule_engine_converges_without_eval",
    "E11": "test_e11_hermeneutic_separates_source_context_and_hypothesis",
    "E12": "test_e12_formalization_builds_symbolic_expression_without_eval",
    "E13": "test_e13_json_schema_validation_positive_and_negative",
    "E14": "test_e14_provenance_chain_detects_tampering",
    "E15": "test_e15_consensus_requires_all_assigned_votes_and_same_evidence",
}


def _flatten_test_ids(suite) -> list[str]:
    identifiers = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            identifiers.extend(_flatten_test_ids(item))
        else:
            identifiers.append(item.id())
    return identifiers


def run_unittests() -> dict[str, Any]:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for module_name in TEST_MODULES:
        module = importlib.import_module(module_name)
        suite.addTests(loader.loadTestsFromModule(module))
    test_ids = _flatten_test_ids(suite)
    engine_ids_covered = sorted(
        engine_id for engine_id, matcher in REQUIRED_ENGINE_TEST_MATCHERS.items()
        if any(matcher in test_id for test_id in test_ids)
    )
    command_route_matrix_test = any(
        "test_complete_canonical_route_matrix_for_all_fourteen_commands" in test_id
        for test_id in test_ids
    )
    # Never run acceptance tests against the user's persistent vector database.
    # Each target-validation run receives a fresh, disposable Qdrant directory.
    previous_vector_path = os.environ.get("LUNITA_VECTOR_DB_PATH")
    with tempfile.TemporaryDirectory(prefix="lunita-target-engine-tests-") as vector_db:
        os.environ["LUNITA_VECTOR_DB_PATH"] = vector_db
        try:
            result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
        finally:
            if previous_vector_path is None:
                os.environ.pop("LUNITA_VECTOR_DB_PATH", None)
            else:
                os.environ["LUNITA_VECTOR_DB_PATH"] = previous_vector_path
    return {
        "status": "PASS" if result.wasSuccessful() and not result.skipped else "FAIL",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "engine_ids_covered": engine_ids_covered,
        "required_engine_ids": sorted(REQUIRED_ENGINE_TEST_MATCHERS),
        "command_route_matrix_test_present": command_route_matrix_test,
        "failure_test_ids": [test.id() for test, _ in result.failures],
        "error_test_ids": [test.id() for test, _ in result.errors],
        "skipped_test_ids": [test.id() for test, _ in result.skipped],
        "test_ids": test_ids,
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
    for arguments in LEGACY_SMOKE_COMMANDS:
        command = " ".join(arguments)
        rc = launcher.run_legacy(list(arguments))
        results[command] = {"returncode": rc, "status": "PASS" if rc == 0 else "FAIL"}
        if rc != 0:
            raise TargetGateError(f"Legacy application/fault smoke test failed: {command} rc={rc}")
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
        "target": str(ROOT),
        "status": "BLOCKED",
        "certification": "NOT_GRANTED",
        "canonical_g06_certification": "NOT_GRANTED",
        "canonical_g08_binding_mutation": False,
    }
    try:
        report["rootfs_build"] = verify_rootfs_build_receipt()
        overlay = verify_overlay()
        import engine_runtime_v1 as engine
        registry = engine.validate_registry()
        dependencies = engine.engine_dependency_inventory()
        if dependencies["status"] != "PASS":
            raise TargetGateError("Runtime dependencies are missing: " + ", ".join(dependencies["missing"]))
        report["overlay_integrity"] = overlay
        report["e04_quantization"] = verify_e04_quantization_receipt()
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
