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
import stat
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
    """Enumerate hash-verifiable regular files, recursively and without following links.

    With no filter, return every regular file. The previous implementation returned
    an empty list for that valid call shape, silently disabling fallback discovery
    for externally materialized OPA/Dagger and portability executables.
    """
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ProbeBlocked("REGULAR_FILE_SEARCH_ROOT_MISSING_OR_UNSAFE:" + str(root))
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
            matches_name = name is not None and file_name == name
            matches_suffix = suffix is not None and path.suffix.casefold() == suffix.casefold()
            if matches_name or matches_suffix or (name is None and suffix is None):
                found.append(path)
    return found


def materialized_asset_root(root: Path, asset_id: str) -> Path:
    """Resolve an asset's exact expansion path from the hash-pinned placement manifest."""
    root = Path(root).resolve(strict=True)
    manifest_path = root / "EXTERNALIZED_ASSET_PLACEMENT.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ProbeBlocked("EXTERNALIZED_ASSET_PLACEMENT_MISSING")
    placement = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = [row for row in placement.get("assets", []) if isinstance(row, dict) and row.get("id") == asset_id]
    if len(rows) != 1:
        raise ProbeFailure("EXTERNALIZED_ASSET_ID_NOT_UNIQUE:" + asset_id)
    row = rows[0]
    declared = row.get("expanded_path")
    prefix = "cajita-luna-runtime/"
    if not isinstance(declared, str) or not declared.startswith(prefix):
        raise ProbeFailure("EXTERNALIZED_ASSET_EXPANDED_PATH_INVALID:" + asset_id)
    relative = Path(declared[len(prefix):])
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ProbeFailure("EXTERNALIZED_ASSET_EXPANDED_PATH_UNSAFE:" + asset_id)
    target = root / relative
    if target.is_symlink() or not target.is_dir() or not target.resolve().is_relative_to(root):
        raise ProbeBlocked("EXTERNALIZED_ASSET_NOT_MATERIALIZED_AT_REGISTERED_PATH:" + asset_id)
    descriptor_path = target / "CAJITA_MODULE.json"
    if descriptor_path.is_symlink() or not descriptor_path.is_file():
        raise ProbeFailure("EXTERNALIZED_ASSET_DESCRIPTOR_MISSING:" + asset_id)
    descriptor_bytes = descriptor_path.read_bytes()
    descriptor = json.loads(descriptor_bytes.decode("utf-8"))
    expected_descriptor_sha = row.get("factory_reconciliation", {}).get("module_manifest_sha256")
    if (
        descriptor.get("canonical_asset_id") != asset_id
        or descriptor.get("module_key") != relative.as_posix()
        or not isinstance(expected_descriptor_sha, str)
        or sha256_bytes(descriptor_bytes) != expected_descriptor_sha
    ):
        raise ProbeFailure("EXTERNALIZED_ASSET_DESCRIPTOR_BINDING_MISMATCH:" + asset_id)
    return target


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


def native_engine_build(root: Path, target_id: str) -> dict[str, Any]:
    """Resolve only build outputs covered by the runtime's factory receipt."""
    receipt_path = root / "NATIVE_ENGINE_BUILD_RECEIPTS.json"
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ProbeBlocked("NATIVE_ENGINE_BUILD_RECEIPT_MISSING")
    routing_path = root / "command_subdomain_routing.json"
    if routing_path.is_symlink() or not routing_path.is_file():
        raise ProbeFailure("NATIVE_ENGINE_ROUTING_REGISTRY_MISSING")
    routing = json.loads(routing_path.read_text(encoding="utf-8"))
    materialization = routing.get("materialization", {})
    if materialization.get("native_engine_build_receipt") != receipt_path.name:
        raise ProbeFailure("NATIVE_ENGINE_BUILD_RECEIPT_NOT_BOUND")
    if materialization.get("native_engine_build_receipt_sha256") != sha256_file(receipt_path):
        raise ProbeFailure("NATIVE_ENGINE_BUILD_RECEIPT_HASH_MISMATCH")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "CAJITA_NATIVE_ENGINE_BUILD_RECEIPTS/1.0":
        raise ProbeFailure("NATIVE_ENGINE_BUILD_RECEIPT_SCHEMA_INVALID")
    matches = [row for row in receipt.get("builds", []) if row.get("target_id") == target_id]
    if len(matches) != 1 or matches[0].get("build_status") != "PASS" or matches[0].get("source_tree_preserved") is not True:
        raise ProbeBlocked("NATIVE_ENGINE_BUILD_NOT_VALIDATED:" + target_id)
    build = matches[0]
    outputs = build.get("binary_artifacts")
    if not isinstance(outputs, list) or not outputs:
        raise ProbeBlocked("NATIVE_ENGINE_BINARY_RECEIPT_MISSING:" + target_id)
    for row in outputs + build.get("shared_libraries", []):
        rel = row.get("path")
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise ProbeFailure("NATIVE_ENGINE_RECEIPT_PATH_UNSAFE")
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise ProbeBlocked("NATIVE_ENGINE_RECEIPT_ARTIFACT_MISSING:" + rel)
        if path.stat().st_size != row.get("bytes") or sha256_file(path) != row.get("sha256"):
            raise ProbeFailure("NATIVE_ENGINE_RECEIPT_ARTIFACT_IDENTITY_MISMATCH:" + rel)
    return build


def native_binary(root: Path, build: dict[str, Any], name: str) -> Path:
    """Return an executable whose bytes are exactly the receipt-verified build output.

    Distribution archives can preserve the correct native executable bytes while
    losing POSIX execute bits. Never chmod the source artifact in place: materialize
    a byte-identical executable copy in the writable diagnostic workspace and bind
    the copy to the original receipt hash. This repairs an extraction/mode defect,
    not the executable contents or source model weights.
    """
    matches = [row for row in build["binary_artifacts"] if row.get("name") == name]
    if len(matches) != 1:
        raise ProbeFailure("NATIVE_ENGINE_RECEIPT_BINARY_NAME_MISMATCH:" + name)
    row = matches[0]
    relative = row.get("path")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ProbeFailure("NATIVE_ENGINE_RECEIPT_BINARY_PATH_UNSAFE:" + name)
    binary = root / relative
    if binary.is_symlink() or not binary.is_file():
        raise ProbeBlocked("NATIVE_ENGINE_RECEIPT_BINARY_MISSING:" + name)
    source_mode = stat.S_IMODE(binary.stat().st_mode)
    source_bytes = binary.read_bytes()
    source_sha256 = sha256_bytes(source_bytes)
    if len(source_bytes) != row.get("bytes") or source_sha256 != row.get("sha256"):
        raise ProbeFailure("NATIVE_ENGINE_RECEIPT_ARTIFACT_IDENTITY_MISMATCH:" + name)
    if binary.stat().st_mode & 0o111:
        return binary

    target_id = str(build.get("target_id", ""))
    if not target_id or "/" in target_id or "\\" in target_id or target_id in {".", ".."}:
        raise ProbeFailure("NATIVE_ENGINE_RECEIPT_TARGET_ID_UNSAFE")
    cache_root = root / ".louksnapg-verified-executables"
    if cache_root.is_symlink():
        raise ProbeFailure("VERIFIED_EXEC_CACHE_SYMLINK_REJECTED")
    cache_root.mkdir(mode=0o700, exist_ok=True)
    if cache_root.is_symlink() or not cache_root.is_dir() or not cache_root.resolve().is_relative_to(root.resolve()):
        raise ProbeFailure("VERIFIED_EXEC_CACHE_ROOT_UNSAFE")
    target_root = cache_root / target_id
    if target_root.is_symlink():
        raise ProbeFailure("VERIFIED_EXEC_TARGET_DIRECTORY_SYMLINK_REJECTED")
    target_root.mkdir(mode=0o700, exist_ok=True)
    if target_root.is_symlink() or not target_root.is_dir() or not target_root.resolve().is_relative_to(cache_root.resolve()):
        raise ProbeFailure("VERIFIED_EXEC_TARGET_DIRECTORY_UNSAFE")
    executable = target_root / name
    if executable.is_symlink():
        raise ProbeFailure("VERIFIED_EXEC_COPY_SYMLINK_REJECTED:" + name)
    if executable.exists() and (not executable.is_file() or executable.stat().st_size == 0):
        raise ProbeFailure("VERIFIED_EXEC_COPY_DESTINATION_UNSAFE:" + name)
    if executable.exists():
        copied_bytes = executable.read_bytes()
        if copied_bytes != source_bytes or sha256_bytes(copied_bytes) != source_sha256:
            raise ProbeFailure("VERIFIED_EXEC_COPY_COLLISION:" + name)
    else:
        copy_executable(binary, executable)
    os.chmod(executable, 0o755)
    copied_bytes = executable.read_bytes()
    if copied_bytes != source_bytes or sha256_bytes(copied_bytes) != source_sha256:
        raise ProbeFailure("VERIFIED_EXEC_COPY_IDENTITY_MISMATCH:" + name)
    if not (executable.stat().st_mode & 0o111):
        raise ProbeFailure("VERIFIED_EXEC_COPY_MODE_NOT_EXECUTABLE:" + name)
    if binary.read_bytes() != source_bytes or stat.S_IMODE(binary.stat().st_mode) != source_mode:
        raise ProbeFailure("NATIVE_EXEC_MATERIALIZATION_MUTATED_SOURCE_ARTIFACT:" + name)
    return executable


def native_library_environment(root: Path, build: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    dirs = sorted({str((root / row["path"]).parent) for row in build.get("shared_libraries", [])})
    previous = env.get("LD_LIBRARY_PATH", "")
    values = dirs + ([previous] if previous else [])
    if values:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(values)
    return env


def probe_trealla(root: Path) -> dict[str, Any]:
    module,descriptor=module_for(root,"D04_HERMENEUTICA_HG")
    source=module/"trealla-2.100.24"/"trealla-2.100.24"
    build=native_engine_build(root,"D04_HERMENEUTICA_HG")
    binary=native_binary(root,build,"tpl")
    grammar=source/"samples"/"grammar.pl"
    if grammar.is_symlink() or not grammar.is_file():
        raise ProbeFailure("TREALLA_GRAMMAR_FIXTURE_MISSING")
    # Trealla documents DCG support via library(dcgs); phrase/2 is not
    # assumed to be implicitly imported by the runtime. The bundled upstream
    # grammar accepts "the man shoots" (sentence -> np, vp -> verb).
    query="use_module(library(dcgs)),phrase(sentence,[the,man,shoots])"
    run=require_ok(run_process([str(binary),"-g",query,"-l","samples/grammar.pl"],cwd=source,timeout=15,env=native_library_environment(root,build)),"TREALLA_PACKAGED_PROLOG_QUERY_FAILED")
    if "true" not in str(run.get("stdout_excerpt","")).casefold():
        raise ProbeFailure("TREALLA_PACKAGED_PROLOG_QUERY_NOT_TRUE:"+str(run.get("stdout_excerpt",""))[-500:])
    return {
        "status":PASS,"primitive":"PACKAGED_TREALLA_PROLOG_GRAMMAR_QUERY",
        "binary_sha256":sha256_file(binary),"grammar_sha256":sha256_file(grammar),
        "module_tree_sha256_declared":descriptor.get("tree_integrity",{}).get("sha256"),
        "native_build_receipt_sha256":sha256_file(root/"NATIVE_ENGINE_BUILD_RECEIPTS.json"),
        "consumer_task_equivalence":"NOT_ESTABLISHED_FULL_HERMENEUTICS",
        "task_coverage":"PROLOG_GRAMMAR_PRIMITIVE_ONLY_NOT_FULL_HISTORICAL_HERMENEUTICS",
        "packaged_binary_execution":True,"runtime_output_sha256":sha256_bytes(str(run.get("stdout_excerpt","")).encode()),
        "certification":"NOT_GRANTED"
    }


def probe_foma(root: Path) -> dict[str, Any]:
    module,descriptor=module_for(root,"D04_TRADUCCION_LENGUAS_ANTIGUAS")
    source=module/"foma-master"/"foma-master"/"foma"
    build=native_engine_build(root,"D04_TRADUCCION_LENGUAS_ANTIGUAS")
    foma_binary=native_binary(root,build,"foma")
    flookup_binary=native_binary(root,build,"flookup")
    env=native_library_environment(root,build)
    version=require_ok(run_process([str(foma_binary),"-v"],cwd=source,timeout=15,env=env),"FOMA_PACKAGED_VERSION_FAILED")
    lookup_version=require_ok(run_process([str(flookup_binary),"-v"],cwd=source,timeout=15,env=env),"FLOOKUP_PACKAGED_VERSION_FAILED")
    with tempfile.TemporaryDirectory(prefix="foma-packaged-primitive-") as temp:
        temp_path=Path(temp)
        script=temp_path/"primitive.foma"
        # Foma regex transducers use an explicit upper:lower pair for a
        # direct lexical mapping. "->" expresses a replacement rule, not
        # this one-entry lexical transducer.
        script.write_text("regex cat:gato;\nsave stack primitive.fst\nquit\n",encoding="utf-8")
        compiled=require_ok(run_process([str(foma_binary),"-q","-f",str(script)],cwd=temp_path,timeout=30,env=env),"FOMA_PACKAGED_TRANSDUCER_BUILD_FAILED")
        fst=temp_path/"primitive.fst"
        if fst.is_symlink() or not fst.is_file() or fst.stat().st_size==0:
            raise ProbeFailure("FOMA_PACKAGED_TRANSDUCER_MISSING")
        lookup=require_ok(run_process([str(flookup_binary),str(fst)],cwd=temp_path,timeout=15,env=env,stdin="cat\n"),"FLOOKUP_PACKAGED_EXECUTION_FAILED")
        lookup_text=str(lookup.get("stdout_excerpt",""))
        if "gato" not in lookup_text.casefold():
            raise ProbeFailure("FOMA_PACKAGED_TRANSLATION_FIXTURE_MISMATCH:"+lookup_text[-500:])
        fixture_sha=sha256_file(script)
        transducer_sha=sha256_file(fst)
        runtime_output_sha=sha256_bytes((str(compiled.get("stdout_excerpt",""))+lookup_text).encode())
    with tempfile.TemporaryDirectory(prefix="foma-source-regression-") as temp:
        build_root=Path(temp)/"foma-source"
        shutil.copytree(source,build_root,symlinks=False)
        test_runner=build_root/"tests"/"run.sh"
        if test_runner.is_symlink() or not test_runner.is_file():
            raise ProbeFailure("FOMA_UPSTREAM_TEST_RUNNER_MISSING_OR_UNSAFE")
        source_runner=source/"tests"/"run.sh"
        source_runner_sha=sha256_file(source_runner)
        if sha256_file(test_runner)!=source_runner_sha:
            raise ProbeFailure("FOMA_UPSTREAM_TEST_RUNNER_COPY_HASH_MISMATCH")
        os.chmod(test_runner,stat.S_IMODE(test_runner.stat().st_mode)|0o111)
        check_env=env.copy()
        local_build_lib=build_root/"src"/"libfoma"/".libs"
        if local_build_lib.is_dir():
            previous=check_env.get("LD_LIBRARY_PATH","")
            check_env["LD_LIBRARY_PATH"]=str(local_build_lib)+(os.pathsep+previous if previous else "")
        regression=require_ok(run_process(["make","check"],cwd=build_root,timeout=900,env=check_env),"FOMA_UPSTREAM_REGRESSION_FAILED")
        if sha256_file(source_runner)!=source_runner_sha or source_runner.stat().st_mode&0o111:
            raise ProbeFailure("FOMA_UPSTREAM_SOURCE_RUNNER_MUTATED")
    return {
        "status":PASS,"primitive":"PACKAGED_FOMA_FLOOKUP_FINITE_STATE_TRANSLATION",
        "foma_sha256":sha256_file(foma_binary),"flookup_sha256":sha256_file(flookup_binary),
        "foma_version_sha256":sha256_bytes(str(version.get("stdout_excerpt","")).encode()),
        "flookup_version_sha256":sha256_bytes(str(lookup_version.get("stdout_excerpt","")).encode()),
        "fixture_sha256":fixture_sha,"transducer_sha256":transducer_sha,
        "consumer_task_equivalence":"NOT_ESTABLISHED_ANCIENT_LANGUAGE_LEXICON_MISSING",
        "task_coverage":"FINITE_STATE_ENGINE_PRIMITIVE_ONLY_NOT_FULL_ANCIENT_LANGUAGE_TRANSLATION",
        "packaged_binary_execution":True,"upstream_regression_status":"PASS",
        "source_tree_sha256_declared":descriptor.get("tree_integrity",{}).get("sha256"),
        "native_build_receipt_sha256":sha256_file(root/"NATIVE_ENGINE_BUILD_RECEIPTS.json"),
        "runtime_output_sha256":runtime_output_sha,
        "certification":"NOT_GRANTED"
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
    dagger_root = materialized_asset_root(root, "DAGGER_0_21_8_LINUX_AMD64")
    opa_root = materialized_asset_root(root, "OPA_STATIC_LINUX_AMD64_CANDIDATE")
    # Discover executable names only inside their separately hash-pinned asset trees.
    candidates = [
        p for p in regular_files(opa_root)
        if p.name.casefold() in {"opa", "opa_static", "opa_linux_amd64_static"}
        or p.name.casefold().startswith("opa_")
    ]
    dagger_candidates = [
        p for p in regular_files(dagger_root)
        if p.name.casefold() == "dagger" or p.name.casefold().startswith("dagger_")
    ]
    opa_source = next((p for p in candidates if p.is_file() and p.stat().st_size > 100_000), None)
    dagger_source = next((p for p in dagger_candidates if p.is_file() and p.stat().st_size > 100_000), None)
    if opa_source is None or dagger_source is None:
        discovered = {
            "opa_files": [p.relative_to(opa_root).as_posix() for p in regular_files(opa_root)[:30]],
            "dagger_files": [p.relative_to(dagger_root).as_posix() for p in regular_files(dagger_root)[:30]],
        }
        raise ProbeBlocked("OPA_OR_DAGGER_EXECUTABLE_NOT_FOUND_IN_REGISTERED_ASSET_TREES:" + json.dumps(discovered, sort_keys=True)[:1000])
    with tempfile.TemporaryDirectory(prefix="louksnapg-policy-") as temp:
        tmp = Path(temp)
        opa = copy_executable(opa_source, tmp / "opa")
        dagger = copy_executable(dagger_source, tmp / "dagger")
        version = require_ok(run_process([str(dagger), "version"], cwd=tmp, timeout=30), "DAGGER_VERSION_PROBE_FAILED")
        policy = tmp / "release.rego"
        policy.write_text(rego_release_policy(), encoding="utf-8")

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
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read(1200).decode("utf-8", errors="replace")
        raise ProbeFailure("HTTP_POST_FAILED:status=" + str(exc.code) + ":url=" + url.split("?", 1)[0] + ":body=" + body) from exc


def rqlite_ready_body_is_complete(http_status: int, body: str) -> bool:
    """Require rqlite's documented /readyz leader/store conditions before writes."""
    if isinstance(http_status, bool) or http_status != 200 or not isinstance(body, str):
        return False
    normalized = body.casefold()
    return "leader ok" in normalized and "store ok" in normalized


def wait_for_rqlite_ready(base: str, process: subprocess.Popen, timeout_seconds: int = 25) -> dict[str, Any]:
    """Wait for a write-ready Raft leader, not merely a live HTTP status endpoint.

    rqlite's /status can answer before leader election. /readyz reports node,
    leader, and store readiness, and prevents the first database write from racing
    the single-node election.
    """
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    last_observation = "NO_RESPONSE"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ProbeBlocked("RQLITE_PROCESS_EXITED_BEFORE_LEADER_READY")
        attempts += 1
        try:
            with urllib.request.urlopen(base + "/readyz", timeout=1) as response:
                body = response.read(2048).decode("utf-8", errors="replace")
                if rqlite_ready_body_is_complete(response.status, body):
                    return {
                        "endpoint": "/readyz",
                        "http_status": response.status,
                        "attempts": attempts,
                        "body_sha256": sha256_bytes(body.encode("utf-8")),
                        "ready_state": "NODE_LEADER_STORE_READY",
                    }
                last_observation = "HTTP_" + str(response.status) + ":" + body[:180].replace("\\n", " ")
        except urllib.error.HTTPError as exc:
            body = exc.read(512).decode("utf-8", errors="replace")
            last_observation = "HTTP_" + str(exc.code) + ":" + body[:180].replace("\\n", " ")
        except Exception as exc:
            last_observation = type(exc).__name__
        time.sleep(0.25)
    raise ProbeBlocked("RQLITE_LEADER_READINESS_TIMEOUT:" + last_observation)


def rqlite_statement_batch(*statements: str) -> list[str]:
    """Return the rqlite HTTP API's JSON array of SQL strings."""
    if not statements or any(not isinstance(statement, str) or not statement.strip() for statement in statements):
        raise ValueError("RQLITE_SQL_STATEMENT_BATCH_INVALID")
    return list(statements)


def rego_release_policy() -> str:
    """Return valid OPA 1.x / Rego v1 syntax."""
    return (
        "package louksnapg.release\n"
        "default allow := false\n"
        "allow if {\n"
        "  input.action == \"promote\"\n"
        "  input.tests_passed == true\n"
        "  input.g23 == \"PASS\"\n"
        "}\n"
    )

def sqlite_migration_probe(source_root: Path, temp_path: Path) -> dict[str, Any]:
    """Build the SQLite CLI from the pinned canonical source tree, not absent amalgamation files.

    sqlite-src is the canonical source bundle and intentionally need not contain the
    generated sqlite3.c/shell.c amalgamation pair. SQLite's official build instructions
    use the source tree's configure script followed by `make sqlite3`; all writes occur
    in a temporary byte-identical copy, preserving the hash-pinned materialized input.
    """
    configure_candidates = regular_files(source_root, name="configure")
    configure_candidates = [p for p in configure_candidates if os.access(p, os.R_OK)]
    if not configure_candidates:
        raise ProbeBlocked("SQLITE_CANONICAL_SOURCE_CONFIGURE_NOT_FOUND")
    configure_source = min(configure_candidates, key=lambda p: (len(p.relative_to(source_root).parts), p.relative_to(source_root).as_posix()))
    source_tree = configure_source.parent
    if source_tree.is_symlink() or not source_tree.is_dir() or not source_tree.resolve().is_relative_to(source_root.resolve()):
        raise ProbeFailure("SQLITE_CANONICAL_SOURCE_ROOT_UNSAFE")
    expected_source_tree_hash = sha256_bytes(json.dumps(
        [{"path": p.relative_to(source_tree).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
         for p in sorted(source_tree.rglob("*"), key=lambda p:p.relative_to(source_tree).as_posix().encode("utf-8"))
         if p.is_file() and not p.is_symlink()],
        sort_keys=True, separators=(",", ":")
    ).encode("utf-8"))
    build_root = temp_path / "sqlite-source-build"
    if build_root.exists() or build_root.is_symlink():
        raise ProbeFailure("SQLITE_BUILD_DESTINATION_COLLISION")
    shutil.copytree(source_tree, build_root, symlinks=False)
    configure_copy = build_root / configure_source.name
    configure_build = require_ok(
        run_process(["sh", str(configure_copy)], cwd=build_root, timeout=300),
        "SQLITE_CANONICAL_CONFIGURE_FAILED",
    )
    build = require_ok(
        run_process(["make", "-j1", "sqlite3"], cwd=build_root, timeout=900),
        "SQLITE_CANONICAL_BUILD_FAILED",
    )
    binary = build_root / "sqlite3"
    if binary.is_symlink() or not binary.is_file() or not (binary.stat().st_mode & 0o111):
        raise ProbeFailure("SQLITE_CANONICAL_BUILD_OUTPUT_MISSING_OR_NOT_EXECUTABLE")
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
    return {"configure": configure_build, "build": build, "migration": result,
            "database_sha256": sha256_file(database), "source_tree_sha256_before_build": expected_source_tree_hash,
            "built_sqlite_binary_sha256": sha256_file(binary), "sqlite_version": require_ok(
                run_process([str(binary), "--version"], cwd=temp_path, timeout=15), "SQLITE_BUILD_VERSION_PROBE_FAILED"
            )}


def probe_migration_persistence(root: Path) -> dict[str, Any]:
    module, _ = module_for(root, "D06_MIGRACION_PERSISTENCIA")
    receipts = materialize(root, ["RQLITE_10_2_7_LINUX_AMD64", "SQLITE_SOURCE_3_53_4"])
    rqlite_root = materialized_asset_root(root, "RQLITE_10_2_7_LINUX_AMD64")
    sqlite_source_root = materialized_asset_root(root, "SQLITE_SOURCE_3_53_4")
    with tempfile.TemporaryDirectory(prefix="louksnapg-migration-") as temp:
        temp_path = Path(temp)
        migration = sqlite_migration_probe(sqlite_source_root, temp_path)
        binaries = regular_files(rqlite_root, name="rqlited")
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
                ready_receipt = wait_for_rqlite_ready(base, proc, timeout_seconds=25)
                create_status, create = post_json(base + "/db/execute?pretty", rqlite_statement_batch("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT)"))
                insert_status, insert = post_json(base + "/db/execute?pretty", rqlite_statement_batch("INSERT INTO records(id,value) VALUES(1,'durable')"))
                query_status, query = post_json(base + "/db/query?pretty", rqlite_statement_batch("SELECT value FROM records WHERE id=1"))
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
            "rqlite_readiness": ready_receipt,
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
