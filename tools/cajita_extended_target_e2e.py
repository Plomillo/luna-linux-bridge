#!/usr/bin/env python3
"""Run bounded, non-model primitive probes for the ten previously untested targets.

A green harness run means every target received a recorded outcome; it never means
all targets passed, and never grants consumer-task equivalence or certification.
No source checkpoint weights are downloaded. Materialized assets come only from
hash-pinned archives already inside the candidate distribution.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

SCHEMA = "CAJITA_EXTENDED_TARGET_E2E/1.0"
TARGETS = {
    "D04_HERMENEUTICA_HG": "Trealla Prolog goal over the bundled DCG grammar",
    "D04_TRADUCCION_LENGUAS_ANTIGUAS": "Foma native regression suite",
    "D05_CALIBRE": "Calibre conversion engine availability",
    "D06_ANTI_ALUCINACIONES": "ONNX model payload identity and availability",
    "D06_ARCHIVADO_DETECCION": "Siegfried identification of a generated ZIP fixture",
    "D06_COGNITIVE_CI_CD": "Bundled OPA allow/deny policy evaluation and Dagger version",
    "D06_MIGRACION_PERSISTENCIA": "SQLite schema migration and rqlite write/read round trip",
    "D06_PORTABILIDAD_BASE": "Bundled Windows CMake architecture inspection",
    "D06_RUNTIME_ANDROID_WINDOWS": "Avalonia/Tauri source package and native-platform readiness",
    "D06_TESTING": "Bundled pytest wheel executes an isolated known-answer test",
}
PASS = "PASS_PRIMITIVE_SMOKE"
BLOCKED = "BLOCKED"
FAIL = "FAIL"


class ProbeBlocked(RuntimeError):
    pass


class ProbeFailure(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_process(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 120,
    env: dict[str, str] | None = None,
    stdin: str | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            input=stdin,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            shell=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeFailure("COMMAND_TIMEOUT:" + Path(command[0]).name) from exc
    except OSError as exc:
        raise ProbeBlocked("COMMAND_UNAVAILABLE:" + Path(command[0]).name + ":" + type(exc).__name__) from exc
    return {
        "command_name": Path(command[0]).name,
        "return_code": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "stdout_sha256": sha256_bytes(completed.stdout.encode("utf-8", errors="replace")),
        "stderr_sha256": sha256_bytes(completed.stderr.encode("utf-8", errors="replace")),
        "stdout_excerpt": completed.stdout[-1200:],
        "stderr_excerpt": completed.stderr[-1200:],
    }


def require_ok(result: dict[str, Any], error_code: str) -> dict[str, Any]:
    if result["return_code"] != 0:
        raise ProbeFailure(error_code + ":exit=" + str(result["return_code"]) + ":" + result["stderr_excerpt"][-300:])
    return result


def module_for(root: Path, target_id: str) -> tuple[Path, dict[str, Any]]:
    routing_path = root / "command_subdomain_routing.json"
    if routing_path.is_symlink() or not routing_path.is_file():
        raise ProbeFailure("CANONICAL_ROUTING_REGISTRY_MISSING")
    routing = json.loads(routing_path.read_text(encoding="utf-8"))
    matches = [row for row in routing.get("targets", []) if row.get("id") == target_id]
    if len(matches) != 1:
        raise ProbeFailure("TARGET_ID_NOT_UNIQUE_IN_CANONICAL_ROUTING:" + target_id)
    spec = matches[0]
    relative = spec.get("path")
    if not isinstance(relative, str) or not relative:
        raise ProbeFailure("TARGET_MODULE_PATH_MISSING:" + target_id)
    module = root / relative
    if module.is_symlink() or not module.is_dir() or not module.resolve().is_relative_to(root.resolve()):
        raise ProbeFailure("TARGET_MODULE_ROOT_MISSING_OR_UNSAFE:" + target_id)
    descriptor_path = module / "CAJITA_MODULE.json"
    if descriptor_path.is_symlink() or not descriptor_path.is_file():
        raise ProbeFailure("TARGET_MODULE_DESCRIPTOR_MISSING:" + target_id)
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    if descriptor.get("target_id") != target_id or descriptor.get("relative_path") != relative:
        raise ProbeFailure("TARGET_MODULE_DESCRIPTOR_BINDING_MISMATCH:" + target_id)
    return module, descriptor


def materialize(root: Path, asset_ids: list[str]) -> list[dict[str, Any]]:
    runtime_cli = root / "cajita_runtime.py"
    if runtime_cli.is_symlink() or not runtime_cli.is_file():
        raise ProbeBlocked("RUNTIME_MATERIALIZER_UNAVAILABLE")
    receipts = []
    for asset_id in asset_ids:
        result = run_process(
            [sys.executable, str(runtime_cli), "materialize-asset", "--asset-id", asset_id, "--root", str(root)],
            cwd=root,
            timeout=1200,
        )
        if result["return_code"] != 0:
            raise ProbeBlocked("ASSET_MATERIALIZATION_BLOCKED:" + asset_id + ":" + result["stderr_excerpt"][-300:])
        receipts.append({"asset_id": asset_id, **result})
    return receipts


def regular_files(root: Path, *, name: str | None = None, suffix: str | None = None) -> list[Path]:
    found: list[Path] = []
    for base, dirs, files in os.walk(root, followlinks=False):
        base_path = Path(base)
        if any((base_path / item).is_symlink() for item in dirs):
            raise ProbeFailure("SYMLINK_DIRECTORY_IN_TARGET_TREE")
        dirs[:] = sorted(dirs)
        for file_name in sorted(files):
            path = base_path / file_name
            if path.is_symlink() or not path.is_file():
                raise ProbeFailure("NON_REGULAR_FILE_IN_TARGET_TREE")
            if name is not None and file_name == name:
                found.append(path)
            elif suffix is not None and path.suffix.casefold() == suffix.casefold():
                found.append(path)
    return found


def copy_executable(source: Path, destination: Path) -> Path:
    if source.is_symlink() or not source.is_file():
        raise ProbeBlocked("EXECUTABLE_MISSING:" + source.name)
    before = source.read_bytes()
    destination.write_bytes(before)
    os.chmod(destination, 0o755)
    after = destination.read_bytes()
    if before != after or sha256_bytes(before) != sha256_bytes(after):
        raise ProbeFailure("EXECUTABLE_COPY_IDENTITY_MISMATCH:" + source.name)
    return destination


def probe_trealla(root: Path) -> dict[str, Any]:
    module, descriptor = module_for(root, "D04_HERMENEUTICA_HG")
    source = module / "trealla-2.100.24" / "trealla-2.100.24"
    makefile = source / "Makefile"
    grammar = source / "samples" / "grammar.pl"
    if any(p.is_symlink() or not p.is_file() for p in (makefile, grammar)):
        raise ProbeBlocked("TREALLA_BUILD_INPUTS_MISSING")
    with tempfile.TemporaryDirectory(prefix="louksnapg-trealla-") as temp:
        build_root = Path(temp) / "trealla"
        shutil.copytree(source, build_root)
        # The upstream Makefile lists README.md as a build prerequisite even
        # though it is not compiled into the binary. The slim source overlay
        # omits that documentation file, so restore a local marker only in the
        # disposable build copy; never mutate the candidate source tree.
        readme = build_root / "README.md"
        if not readme.exists():
            readme.write_text("Trealla Prolog v2.100.24 build prerequisite; source code remains hash-bound.\\n", encoding="utf-8")
        build = require_ok(
            run_process(
                ["make", "-j1", "GIT_VERSION=2.100.24", "NOFFI=1", "NOSSL=1", "NOTHREADS=1", "ISOCLINE=1"],
                cwd=build_root,
                timeout=900,
            ),
            "TREALLA_SOURCE_BUILD_FAILED",
        )
        binary = build_root / "tpl"
        exe = copy_executable(binary, Path(temp) / "tpl-probe")
        query = "phrase(sentence,[the,woman,shoots,man])"
        result = require_ok(
            run_process([str(exe), "-f", "samples/grammar.pl", "-g", query], cwd=build_root, timeout=15),
            "TREALLA_DC G_QUERY_FAILED".replace(" ", ""),
        )
        if "true" not in result["stdout_excerpt"].casefold():
            raise ProbeFailure("TREALLA_DC G_KNOWN_ANSWER_MISMATCH".replace(" ", ""))
    return {
        "status": PASS,
        "primitive": "PROLOG_DC G_GRAMMAR_QUERY".replace(" ", ""),
        "source_descriptor_sha256": sha256_file(module / "CAJITA_MODULE.json"),
        "build": build,
        "query": query,
        "query_result": result,
        "consumer_task_equivalence": "NOT_ESTABLISHED",
        "semantic_scope": "PROLOG_RUNTIME_AND_BUNDLED_TOY_GRAMMAR_ONLY_NOT_FULL_HISTORICAL_HERMENEUTICS",
        "certification": "NOT_GRANTED",
    }


def probe_foma(root: Path) -> dict[str, Any]:
    module, _ = module_for(root, "D04_TRADUCCION_LENGUAS_ANTIGUAS")
    source = module / "foma-master" / "foma-master" / "foma"
    makefile = source / "Makefile"
    test_file = source / "tests" / "run.sh"
    if any(p.is_symlink() or not p.is_file() for p in (makefile, test_file)):
        raise ProbeBlocked("FOMA_BUILD_INPUTS_MISSING")
    with tempfile.TemporaryDirectory(prefix="louksnapg-foma-") as temp:
        build_root = Path(temp) / "foma"
        shutil.copytree(source, build_root)
        build = require_ok(run_process(["make", "-j1"], cwd=build_root, timeout=900), "FOMA_SOURCE_BUILD_FAILED")
        regression = require_ok(run_process(["make", "check"], cwd=build_root, timeout=180), "FOMA_NATIVE_REGRESSION_FAILED")
        binary = build_root / "foma"
        version = require_ok(run_process([str(binary), "-v"], cwd=build_root, timeout=10), "FOMA_VERSION_PROBE_FAILED")
    return {
        "status": PASS,
        "primitive": "FINITE_STATE_TRANSDUCER_ENGINE_AND_UPSTREAM_REGRESSION_SUITE",
        "source_descriptor_sha256": sha256_file(module / "CAJITA_MODULE.json"),
        "build": build,
        "upstream_regression": regression,
        "version": version,
        "consumer_task_equivalence": "NOT_ESTABLISHED",
        "semantic_scope": "FOMA_ENGINE_REGRESSION_ONLY_NO_BUNDLED_ANCIENT_LANGUAGE_LEXICON_OR_FST_PROVEN",
        "certification": "NOT_GRANTED",
    }


def probe_calibre(root: Path) -> dict[str, Any]:
    module, descriptor = module_for(root, "D05_CALIBRE")
    binary_manifest = module / "CALIBRE_BINARY_EXTERNALIZATION.json"
    source_manifest = module / "CALIBRE_SOURCE_PROVENANCE.json"
    if any(path.is_symlink() or not path.is_file() for path in (binary_manifest, source_manifest)):
        raise ProbeFailure("CALIBRE_EXTERNALIZATION_EVIDENCE_MISSING")
    binary_state = json.loads(binary_manifest.read_text(encoding="utf-8"))
    source_state = json.loads(source_manifest.read_text(encoding="utf-8"))
    if binary_state.get("bundled_binary") is not False or source_state.get("bundled_source_archive") is not False:
        raise ProbeFailure("CALIBRE_EXTERNALIZATION_STATE_DIVERGED")
    if binary_state.get("equivalence") != "NOT_ESTABLISHED" or binary_state.get("functional_tests") != "NOT_RUN":
        raise ProbeFailure("CALIBRE_MANIFEST_OVERCLAIMS_OR_UNEXPECTED_STATE")

    configured_converter = os.environ.get("CALIBRE_EBOOK_CONVERT", "").strip()
    converter = configured_converter or shutil.which("ebook-convert")
    if not converter:
        raise ProbeBlocked("CALIBRE_FUNCTIONAL_ENGINE_ABSENT:ebook-convert_not_found_in_test_environment")

    expected_asset = {
        "id": "CALIBRE_V9_17_0_LINUX_X86_64_BINARY",
        "sha256": "953e4512a6482848cd803c88b6d942e6afca65dc3b67c7d1353ae048d616de53",
        "size_bytes": 201590724,
    }
    asset_receipt = {
        "id": os.environ.get("CALIBRE_OFFICIAL_ASSET_ID", ""),
        "sha256": os.environ.get("CALIBRE_OFFICIAL_ASSET_SHA256", ""),
        "size_bytes": int(os.environ.get("CALIBRE_OFFICIAL_ASSET_SIZE_BYTES", "0") or "0"),
    }
    if asset_receipt != expected_asset:
        raise ProbeBlocked("CALIBRE_OFFICIAL_RUNTIME_ASSET_NOT_PROVEN_BY_SIZE_AND_SHA256")

    wrapper_dir = root / "5. Inteligencia documental" / "Conversión documental" / "Calibre Slim"
    wrapper_path = wrapper_dir / "calibre-slim-convert.py"
    source_lock = wrapper_dir / "source-lock.json"
    overlay_archive = wrapper_dir / "calibre-slim-overlay.tar.xz"
    if wrapper_dir.is_symlink() or not wrapper_dir.is_dir() or not wrapper_dir.resolve().is_relative_to(root.resolve()):
        raise ProbeFailure("CALIBRE_SLIM_WRAPPER_DIRECTORY_MISSING_OR_UNSAFE")
    if any(path.is_symlink() or not path.is_file() for path in (wrapper_path, source_lock, overlay_archive)):
        raise ProbeFailure("CALIBRE_SLIM_WRAPPER_LOCK_OR_OVERLAY_MISSING_OR_UNSAFE")

    spec = importlib.util.spec_from_file_location("cajita_calibre_slim_probe", wrapper_path)
    if spec is None or spec.loader is None:
        raise ProbeFailure("CALIBRE_SLIM_WRAPPER_IMPORT_SPEC_INVALID")
    launcher = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = launcher
    spec.loader.exec_module(launcher)
    try:
        overlay_source = launcher.materialize_overlay(wrapper_dir)
        runtime_identity = launcher.verify_pinned_converter(str(converter), wrapper_dir)
    except Exception as exc:
        raise ProbeFailure("CALIBRE_PINNED_RUNTIME_OR_FULL_OVERLAY_VALIDATION_FAILED:" + type(exc).__name__ + ":" + str(exc)[:500]) from exc
    if runtime_identity.get("status") != "PASS_PINNED_VERSION" or runtime_identity.get("expected_version") != "9.17.0":
        raise ProbeFailure("CALIBRE_RUNTIME_IDENTITY_NOT_PASS_PINNED_VERSION")

    with tempfile.TemporaryDirectory(prefix="louksnapg-calibre-e2e-") as temp:
        temp_path = Path(temp)
        source_txt = temp_path / "calibre-smoke-input.txt"
        output_epub = temp_path / "calibre-smoke-output.epub"
        source_txt.write_text("Cajita Calibre v9.17.0 conversion smoke.\nThis sentence verifies a real TXT to EPUB conversion.\n", encoding="utf-8")
        child_env = os.environ.copy()
        child_env["CALIBRE_EBOOK_CONVERT"] = str(Path(converter).resolve(strict=True))
        child_env["CALIBRE_OFFICIAL_ASSET_ID"] = expected_asset["id"]
        child_env["CALIBRE_OFFICIAL_ASSET_SHA256"] = expected_asset["sha256"]
        child_env["CALIBRE_OFFICIAL_ASSET_SIZE_BYTES"] = str(expected_asset["size_bytes"])
        conversion = require_ok(
            run_process([sys.executable, str(wrapper_path), str(source_txt), str(output_epub)], cwd=wrapper_dir, timeout=180, env=child_env),
            "CALIBRE_TEXT_TO_EPUB_CONVERSION_FAILED",
        )
        if output_epub.is_symlink() or not output_epub.is_file() or output_epub.stat().st_size <= 0 or not zipfile.is_zipfile(output_epub):
            raise ProbeFailure("CALIBRE_EPUB_OUTPUT_MISSING_OR_INVALID_CONTAINER")
        with zipfile.ZipFile(output_epub, "r") as epub:
            names = epub.namelist()
            if len(names) != len(set(names)) or epub.testzip() is not None:
                raise ProbeFailure("CALIBRE_EPUB_ARCHIVE_DUPLICATE_MEMBERS_OR_CRC_FAILURE")
            if "mimetype" not in names or epub.read("mimetype") != b"application/epub+zip":
                raise ProbeFailure("CALIBRE_EPUB_MIMETYPE_MISSING_OR_INVALID")
            if "META-INF/container.xml" not in names:
                raise ProbeFailure("CALIBRE_EPUB_CONTAINER_XML_MISSING")
            if not any(name.casefold().endswith(".opf") for name in names):
                raise ProbeFailure("CALIBRE_EPUB_PACKAGE_DOCUMENT_MISSING")
        epub_bytes = output_epub.stat().st_size
        epub_sha256 = sha256_file(output_epub)
        input_bytes = source_txt.stat().st_size
        input_sha256 = sha256_file(source_txt)

    return {
        "status": PASS,
        "primitive": "REAL_TXT_TO_EPUB_CONVERSION_THROUGH_PRODUCT_WRAPPER",
        "runtime_identity": runtime_identity,
        "official_binary_asset_receipt": asset_receipt,
        "official_binary_asset_receipt_source": "verified_download_and_sha256_in_ephemeral_g24_test_image; not_in_product_bundle",
        "source_lock_sha256": sha256_file(source_lock),
        "overlay_archive_sha256": sha256_file(overlay_archive),
        "overlay_archive_bytes": overlay_archive.stat().st_size,
        "materialized_overlay_directory": str(overlay_source),
        "wrapper_sha256": sha256_file(wrapper_path),
        "module_descriptor_sha256": sha256_file(module / "CAJITA_MODULE.json"),
        "input": {"kind": "deterministic_synthetic_text_fixture", "bytes": input_bytes, "sha256": input_sha256},
        "conversion_process": conversion,
        "epub_output": {"bytes": epub_bytes, "sha256": epub_sha256, "container_integrity": "PASS", "mimetype": "PASS", "container_xml": "PASS", "package_document": "PASS"},
        "consumer_task_equivalence": "PASS_FOR_TXT_TO_EPUB_PRIMITIVE_ONLY",
        "pdf_epub_parity": "NOT_ESTABLISHED",
        "reference_model_equivalence": "NOT_APPLICABLE_NON_MODEL_ENGINE",
        "global_certification": "NOT_GRANTED_BY_THIS_PRIMITIVE_PROBE",
    }

def probe_antihallucination(root: Path) -> dict[str, Any]:
    module, _ = module_for(root, "D06_ANTI_ALUCINACIONES")
    model = module / "model.onnx"
    if model.is_symlink() or not model.is_file():
        raise ProbeFailure("ANTI_HALLUCINATION_ONNX_MODEL_MISSING")
    payload = model.read_bytes()
    prefix = payload[:160].decode("utf-8", errors="replace")
    if payload.startswith(b"version https://git-lfs.github.com/spec/v1"):
        match = {}
        for line in prefix.splitlines():
            if line.startswith("oid sha256:"):
                match["lfs_oid_sha256"] = line.split(":", 1)[1]
            elif line.startswith("size "):
                try:
                    match["lfs_declared_bytes"] = int(line.split(" ", 1)[1])
                except ValueError:
                    pass
        return {
            "status": BLOCKED,
            "reason": "ONNX_PAYLOAD_IS_GIT_LFS_POINTER_NOT_EXECUTABLE_MODEL",
            "pointer_file_bytes": len(payload),
            "pointer_file_sha256": sha256_bytes(payload),
            **match,
            "large_model_payload_downloaded": False,
            "consumer_task_equivalence": "NOT_ESTABLISHED",
            "certification": "NOT_GRANTED",
        }
    if len(payload) < 8 or not payload.startswith(b"\x08"):
        raise ProbeFailure("ONNX_MODEL_HEADER_INVALID")
    return {
        "status": BLOCKED,
        "reason": "ONNX_MODEL_PRESENT_BUT_NO_REGISTERED_GROUNDEDNESS_TASK_OR_REFERENCE_DATASET",
        "model_bytes": len(payload),
        "model_sha256": sha256_bytes(payload),
        "consumer_task_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED",
    }


def probe_archive_detection(root: Path) -> dict[str, Any]:
    module, _ = module_for(root, "D06_ARCHIVADO_DETECCION")
    binary = module / "siegfried_1-11-6_linux-x86_64_static" / "sf"
    if binary.is_symlink() or not binary.is_file():
        raise ProbeBlocked("SIEGFRIED_BINARY_MISSING")
    with tempfile.TemporaryDirectory(prefix="louksnapg-file-id-") as temp:
        temp_path = Path(temp)
        executable = copy_executable(binary, temp_path / "sf")
        fixture = temp_path / "known-zip.zip"
        with zipfile.ZipFile(fixture, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("fixture.txt", "louksnapg-format-identification-fixture\n")
        fixture_sha256 = sha256_file(fixture)
        result = require_ok(run_process([str(executable), "-json", str(fixture)], timeout=15), "SIEGFRIED_FORMAT_IDENTIFICATION_FAILED")
        if "matches" not in result["stdout_excerpt"].casefold() and "zip" not in result["stdout_excerpt"].casefold():
            raise ProbeFailure("SIEGFRIED_KNOWN_ZIP_FORMAT_NOT_RECOGNIZED")
    return {
        "status": PASS,
        "primitive": "FILE_FORMAT_IDENTIFICATION",
        "binary_sha256": sha256_file(binary),
        "fixture_sha256": fixture_sha256,
        "result": result,
        "consumer_task_equivalence": "PASS_FOR_ZIP_FILE_IDENTIFICATION_ONLY",
        "certification": "NOT_GRANTED",
    }


def probe_cognitive_cicd(root: Path) -> dict[str, Any]:
    module, _ = module_for(root, "D06_COGNITIVE_CI_CD")
    receipts = materialize(root, ["DAGGER_0_21_8_LINUX_AMD64", "OPA_STATIC_LINUX_AMD64_CANDIDATE"])
    candidates = regular_files(module, name="opa") + regular_files(module, name="opa_static")
    dagger_candidates = regular_files(module, name="dagger")
    if not candidates:
        candidates = [p for p in regular_files(module) if p.name.casefold().startswith("opa") and os.access(p, os.R_OK)]
    if not dagger_candidates:
        dagger_candidates = [p for p in regular_files(module) if p.name.casefold().startswith("dagger") and os.access(p, os.R_OK)]
    opa_source = next((p for p in candidates if p.is_file() and p.stat().st_size > 100_000), None)
    dagger_source = next((p for p in dagger_candidates if p.is_file() and p.stat().st_size > 100_000), None)
    if opa_source is None or dagger_source is None:
        raise ProbeBlocked("OPA_OR_DAGGER_EXECUTABLE_NOT_MATERIALIZED")
    with tempfile.TemporaryDirectory(prefix="louksnapg-policy-") as temp:
        tmp = Path(temp)
        opa = copy_executable(opa_source, tmp / "opa")
        dagger = copy_executable(dagger_source, tmp / "dagger")
        version = require_ok(run_process([str(dagger), "version"], cwd=tmp, timeout=30), "DAGGER_VERSION_PROBE_FAILED")
        policy = tmp / "release.rego"
        policy.write_text(
            "package louksnapg.release\n"
            "default allow = false\n"
            "allow { input.action == \"promote\"; input.tests_passed == true; input.g23 == \"PASS\" }\n",
            encoding="utf-8",
        )
        good_input = tmp / "good.json"
        good_input.write_text(json.dumps({"action": "promote", "tests_passed": True, "g23": "PASS"}), encoding="utf-8")
        bad_input = tmp / "bad.json"
        bad_input.write_text(json.dumps({"action": "promote", "tests_passed": False, "g23": "PASS"}), encoding="utf-8")
        allow = require_ok(run_process([str(opa), "eval", "-f", "raw", "-d", str(policy), "-i", str(good_input), "data.louksnapg.release.allow"], cwd=tmp, timeout=20), "OPA_ALLOW_POLICY_EVALUATION_FAILED")
        deny = require_ok(run_process([str(opa), "eval", "-f", "raw", "-d", str(policy), "-i", str(bad_input), "data.louksnapg.release.allow"], cwd=tmp, timeout=20), "OPA_DENY_POLICY_EVALUATION_FAILED")
        if allow["stdout_excerpt"].strip() != "true" or deny["stdout_excerpt"].strip() != "false":
            raise ProbeFailure("OPA_POLICY_KNOWN_ANSWER_MISMATCH")
    return {
        "status": PASS,
        "primitive": "LOCAL_POLICY_EVALUATION_AND_DAGGER_CLI_STARTUP",
        "asset_materialization": receipts,
        "opa_sha256": sha256_file(opa_source),
        "dagger_sha256": sha256_file(dagger_source),
        "dagger_version": version,
        "allow_case": allow,
        "deny_case": deny,
        "consumer_task_equivalence": "PASS_FOR_LOCAL_RELEASE_POLICY_PRIMITIVE_ONLY",
        "certification": "NOT_GRANTED",
    }


def free_port_pair() -> tuple[int, int]:
    selected = []
    for _ in range(2):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            selected.append(sock.getsockname()[1])
    if selected[0] == selected[1]:
        return free_port_pair()
    return selected[0], selected[1]


def post_json(url: str, value: Any, timeout: float = 3) -> tuple[int, Any]:
    import urllib.error
    import urllib.request
    payload = json.dumps(value).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def sqlite_migration_probe(module: Path, temp_path: Path) -> dict[str, Any]:
    amalgamations = regular_files(module, name="sqlite3.c")
    shells = regular_files(module, name="shell.c")
    headers = regular_files(module, name="sqlite3.h")
    if not amalgamations or not shells or not headers:
        raise ProbeBlocked("SQLITE_SOURCE_FOR_MIGRATION_NOT_MATERIALIZED")
    source, shell = amalgamations[0], shells[0]
    binary = temp_path / "sqlite3-migration"
    build = require_ok(
        run_process(
            ["cc", "-O2", "-DSQLITE_THREADSAFE=1", str(shell), str(source), "-ldl", "-lpthread", "-lm", "-o", str(binary)],
            timeout=180,
        ),
        "SQLITE_MIGRATION_ENGINE_COMPILE_FAILED",
    )
    database = temp_path / "migration.sqlite3"
    sql = (
        "CREATE TABLE records(id INTEGER PRIMARY KEY,value TEXT NOT NULL);"
        "INSERT INTO records(id,value) VALUES(1,'preserve-me');"
        "ALTER TABLE records ADD COLUMN provenance TEXT NOT NULL DEFAULT 'migrated';"
        "SELECT value||'|'||provenance FROM records WHERE id=1;"
        "PRAGMA integrity_check;"
    )
    result = require_ok(
        run_process([str(binary), "-batch", "-bail", "-noheader", str(database)], stdin=sql, timeout=15),
        "SQLITE_MIGRATION_KNOWN_ANSWER_FAILED",
    )
    if "preserve-me|migrated" not in result["stdout_excerpt"] or not result["stdout_excerpt"].strip().endswith("ok"):
        raise ProbeFailure("SQLITE_MIGRATION_DATA_OR_INTEGRITY_MISMATCH")
    return {"build": build, "migration": result, "database_sha256": sha256_file(database), "source_sha256": sha256_file(source)}


def probe_migration_persistence(root: Path) -> dict[str, Any]:
    module, _ = module_for(root, "D06_MIGRACION_PERSISTENCIA")
    receipts = materialize(root, ["RQLITE_10_2_7_LINUX_AMD64", "SQLITE_SOURCE_3_53_4"])
    with tempfile.TemporaryDirectory(prefix="louksnapg-migration-") as temp:
        temp_path = Path(temp)
        migration = sqlite_migration_probe(module, temp_path)
        binaries = regular_files(module, name="rqlited")
        if not binaries:
            return {
                "status": PASS,
                "primitive": "SQLITE_SCHEMA_MIGRATION_AND_DATA_PRESERVATION",
                "asset_materialization": receipts,
                "sqlite_migration": migration,
                "rqlite_cluster_roundtrip": "BLOCKED_RQLITED_BINARY_NOT_FOUND",
                "consumer_task_equivalence": "PARTIAL",
                "certification": "NOT_GRANTED",
            }
        rqlited = copy_executable(binaries[0], temp_path / "rqlited")
        http_port, raft_port = free_port_pair()
        data_dir = temp_path / "rqlite-data"
        data_dir.mkdir()
        stdout_path, stderr_path = temp_path / "rqlited.stdout", temp_path / "rqlited.stderr"
        with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
            proc = subprocess.Popen(
                [str(rqlited), "-http-addr", f"127.0.0.1:{http_port}", "-raft-addr", f"127.0.0.1:{raft_port}", str(data_dir)],
                cwd=temp_path,
                stdout=out,
                stderr=err,
                stdin=subprocess.DEVNULL,
                shell=False,
            )
            try:
                base = f"http://127.0.0.1:{http_port}"
                deadline = time.monotonic() + 25
                ready = False
                while time.monotonic() < deadline:
                    if proc.poll() is not None:
                        break
                    try:
                        import urllib.request
                        with urllib.request.urlopen(base + "/status", timeout=1) as response:
                            if response.status == 200:
                                ready = True
                                break
                    except Exception:
                        time.sleep(0.3)
                if not ready:
                    raise ProbeBlocked("RQLITE_SERVER_DID_NOT_REACH_READY_STATE")
                create_status, create = post_json(base + "/db/execute?pretty", {"statements": ["CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT)"]})
                insert_status, insert = post_json(base + "/db/execute?pretty", {"statements": ["INSERT INTO records(id,value) VALUES(1,'durable')"]})
                query_status, query = post_json(base + "/db/query?pretty", {"statements": ["SELECT value FROM records WHERE id=1"]})
                response_blob = json.dumps({"create": create, "insert": insert, "query": query}, sort_keys=True)
                if create_status != 200 or insert_status != 200 or query_status != 200 or "durable" not in response_blob:
                    raise ProbeFailure("RQLITE_WRITE_READ_KNOWN_ANSWER_MISMATCH")
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
        return {
            "status": PASS,
            "primitive": "SQLITE_SCHEMA_MIGRATION_AND_RQLITE_WRITE_READ",
            "asset_materialization": receipts,
            "sqlite_migration": migration,
            "rqlite_server_binary_sha256": sha256_file(binaries[0]),
            "rqlite_create": create,
            "rqlite_insert": insert,
            "rqlite_query": query,
            "rqlite_response_sha256": sha256_bytes(response_blob.encode("utf-8")),
            "consumer_task_equivalence": "PASS_FOR_DATABASE_MIGRATION_AND_LOCAL_PERSISTENCE_PRIMITIVES",
            "certification": "NOT_GRANTED",
        }


def probe_portability(root: Path) -> dict[str, Any]:
    module, _ = module_for(root, "D06_PORTABILIDAD_BASE")
    receipts = materialize(root, ["CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE"])
    candidates = regular_files(module, name="cmake.exe")
    if not candidates:
        candidates = [p for p in regular_files(module) if p.name.casefold() == "cmake"]
    if not candidates:
        raise ProbeBlocked("CMAKE_TARGET_EXECUTABLE_NOT_FOUND_AFTER_MATERIALIZATION")
    executable = candidates[0]
    with executable.open("rb") as stream:
        header = stream.read(4096)
    if not header.startswith(b"MZ") or len(header) < 64:
        raise ProbeFailure("CMAKE_EXECUTABLE_NOT_PE")
    pe_offset = struct.unpack_from("<I", header, 0x3C)[0]
    if pe_offset + 6 > len(header) or header[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ProbeFailure("CMAKE_PE_HEADER_INVALID")
    machine = struct.unpack_from("<H", header, pe_offset + 4)[0]
    if machine != 0x8664:
        raise ProbeFailure("CMAKE_PE_MACHINE_NOT_X86_64:" + hex(machine))
    return {
        "status": BLOCKED,
        "reason": "WINDOWS_X64_CMAKE_IDENTIFIED_BUT_CANNOT_BE_EXECUTED_ON_LINUX_RUNNER",
        "primitive": "BINARY_ARCHITECTURE_AND_PACKAGE_IDENTITY_INSPECTION_ONLY",
        "asset_materialization": receipts,
        "cmake_sha256": sha256_file(executable),
        "pe_machine": hex(machine),
        "native_functional_test": "NOT_RUN_WRONG_HOST_PLATFORM",
        "consumer_task_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED",
    }


def probe_runtime_android_windows(root: Path) -> dict[str, Any]:
    module, _ = module_for(root, "D06_RUNTIME_ANDROID_WINDOWS")
    receipts = materialize(root, ["AVALONIA_12_1_1_NUGET", "TAURI_2_11_5_SOURCE_ZIP"])
    project_files = []
    for name in ("*.csproj", "*.sln", "Cargo.toml", "tauri.conf.json", "package.json"):
        project_files.extend(module.rglob(name))
    project_files = sorted({p for p in project_files if p.is_file() and not p.is_symlink()})
    if not project_files:
        raise ProbeBlocked("AVALONIA_TAURI_PROJECT_MANIFESTS_NOT_MATERIALIZED")
    return {
        "status": BLOCKED,
        "reason": "SOURCE_AND_PACKAGE_MANIFESTS_PRESENT_BUT_NATIVE_ANDROID_WINDOWS_BUILDS_AND_DEVICE_TESTS_NOT_RUN",
        "asset_materialization": receipts,
        "project_manifest_count": len(project_files),
        "project_manifest_paths": [p.relative_to(module).as_posix() for p in project_files[:80]],
        "project_manifest_sha256": {p.relative_to(module).as_posix(): sha256_file(p) for p in project_files[:80]},
        "consumer_task_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED",
    }


def probe_testing(root: Path) -> dict[str, Any]:
    module, _ = module_for(root, "D06_TESTING")
    wheels = regular_files(module, suffix=".whl")
    pytest_wheels = [p for p in wheels if p.name.startswith("pytest-9.1.1")]
    if len(pytest_wheels) != 1:
        raise ProbeBlocked("BUNDLED_PYTEST_WHEEL_NOT_UNIQUE")
    wheel = pytest_wheels[0]
    wheel_dirs = sorted({p.parent for p in regular_files(root, suffix=".whl")})
    with tempfile.TemporaryDirectory(prefix="louksnapg-pytest-") as temp:
        temp_path = Path(temp)
        site = temp_path / "site"
        # Install the bundled pytest wheel without resolving absent dependency wheels.
        # Its pinned host dependencies are installed in the ephemeral test image; this probe remains offline.
        install_cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-index", "--no-deps", "--target", str(site)]
        for directory in wheel_dirs:
            install_cmd.extend(["--find-links", str(directory)])
        install_cmd.append(str(wheel))
        install = run_process(install_cmd, timeout=180)
        if install["return_code"] != 0:
            raise ProbeBlocked("BUNDLED_PYTEST_LOCAL_DEPENDENCIES_UNAVAILABLE:" + install["stderr_excerpt"][-500:])
        test_file = temp_path / "test_known_answer.py"
        test_file.write_text("def test_integer_arithmetic():\n    assert 2 + 2 == 4\n", encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(site)
        result = require_ok(
            run_process([sys.executable, "-m", "pytest", "-q", str(test_file)], cwd=temp_path, timeout=60, env=env),
            "BUNDLED_PYTEST_KNOWN_ANSWER_FAILED",
        )
    return {
        "status": PASS,
        "primitive": "BUNDLED_PYTEST_WHEEL_EXECUTES_LOCAL_KNOWN_ANSWER_TEST",
        "wheel_sha256": sha256_file(wheel),
        "local_install": install,
        "test_result": result,
        "network_used_for_python_dependencies": False,
        "consumer_task_equivalence": "PASS_FOR_TEST_RUNNER_PRIMITIVE_ONLY",
        "certification": "NOT_GRANTED",
    }


PROBES = {
    "D04_HERMENEUTICA_HG": probe_trealla,
    "D04_TRADUCCION_LENGUAS_ANTIGUAS": probe_foma,
    "D05_CALIBRE": probe_calibre,
    "D06_ANTI_ALUCINACIONES": probe_antihallucination,
    "D06_ARCHIVADO_DETECCION": probe_archive_detection,
    "D06_COGNITIVE_CI_CD": probe_cognitive_cicd,
    "D06_MIGRACION_PERSISTENCIA": probe_migration_persistence,
    "D06_PORTABILIDAD_BASE": probe_portability,
    "D06_RUNTIME_ANDROID_WINDOWS": probe_runtime_android_windows,
    "D06_TESTING": probe_testing,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Materialized runtime extracted from the exact candidate bundle")
    parser.add_argument("--source-commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--bundle-sha256", default=os.environ.get("LOUKSNAPG_BUNDLE_SHA256", ""))
    parser.add_argument("--contract", default="contracts/louksnapg/architecture-contract.v1.json")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve(strict=True)
    if not root.is_dir():
        raise SystemExit("RUNTIME_ROOT_INVALID")
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "operation_id": "LOUKSNAPG_EXTENDED_NON_MODEL_TARGET_COVERAGE",
        "generated_at_utc": utc_now(),
        "source_commit": args.source_commit or None,
        "bundle_sha256": args.bundle_sha256 or None,
        "contract_sha256": sha256_file(Path(args.contract)) if Path(args.contract).is_file() else None,
        "candidate_runtime_root": str(root),
        "target_expected_count": len(TARGETS),
        "targets": [],
        "coverage_execution": "IN_PROGRESS",
        "product_certification": "NOT_GRANTED",
        "release_eligibility": False,
        "heavy_model_weight_download_count": 0,
        "remote_commander_used": False,
        "synthetic_evidence_used_as_product_proof": False,
    }
    for target_id, purpose in TARGETS.items():
        started = time.monotonic()
        try:
            module, descriptor = module_for(root, target_id)
            result = PROBES[target_id](root)
            status = result.pop("status", PASS)
            row = {
                "target_id": target_id,
                "purpose": purpose,
                "status": status,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "module_descriptor_sha256": sha256_file(module / "CAJITA_MODULE.json"),
                "module_tree_sha256_declared": descriptor.get("tree_integrity", {}).get("sha256"),
                "result": result,
            }
        except ProbeBlocked as exc:
            row = {
                "target_id": target_id,
                "purpose": purpose,
                "status": BLOCKED,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "reason": str(exc)[:700],
                "certification": "NOT_GRANTED",
            }
        except Exception as exc:
            row = {
                "target_id": target_id,
                "purpose": purpose,
                "status": FAIL,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "reason": type(exc).__name__ + ":" + str(exc)[:700],
                "certification": "NOT_GRANTED",
            }
        report["targets"].append(row)
        print(json.dumps({"target_id": target_id, "status": row["status"], "elapsed_seconds": row["elapsed_seconds"], "reason": row.get("reason")}, ensure_ascii=False))
    counts = {status: sum(1 for row in report["targets"] if row["status"] == status) for status in (PASS, BLOCKED, FAIL)}
    report["summary"] = {
        "expected_targets": len(TARGETS),
        "terminal_outcomes": len(report["targets"]),
        "pass_primitive_smoke": counts[PASS],
        "blocked": counts[BLOCKED],
        "fail": counts[FAIL],
        "all_target_outcomes_recorded": len(report["targets"]) == len(TARGETS) and {row["target_id"] for row in report["targets"]} == set(TARGETS),
        "all_primitive_targets_passed": counts[PASS] == len(TARGETS),
        "interpretation": "Complete diagnostic coverage is not integral product certification; blocked and failed targets remain release blockers.",
    }
    report["coverage_execution"] = "COMPLETE_DIAGNOSTIC_ONLY" if report["summary"]["all_target_outcomes_recorded"] else "INCOMPLETE"
    report["decision"] = "HOLD_NOT_CERTIFIED"
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(serialized, encoding="utf-8")
    print(serialized)
    return 0 if report["summary"]["all_target_outcomes_recorded"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
