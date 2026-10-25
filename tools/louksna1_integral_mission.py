#!/usr/bin/env python3
"""Louksna1 integral certification mission.

CUSTOSZ V9 is the worker. It may execute the consumer matrix and journal the
result, but its own completion never grants certification. A separate validator
re-executes the same operations and grants the certificate only when every
mandatory gate passes on that re-execution.

The published structural assessment is not reused as current proof.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote

SCHEMA = "LOUKSNA1_INTEGRAL_DECISION/1.0"
CANDIDATE_ID = "CAJITA_LUNA_RUNTIME_V9_20261023"
WORKFLOW_NAME = "Cajita V9 materialization and Louksna1 governed factory"
CUSTOSZ_SHA256 = "d585b351f617f4d5d134248e0c427d36ee0172b7ec32b0bdef6b7d381d394817"
WORKER_ID = "CUSTOSZV9"
EVALUATOR_ID = "LOUKSNA1_INDEPENDENT_VALIDATOR"
GENESIS_1_1 = "En un principio° creó ’Elohim° los cielos y la tierra."
VERSE_COUNT = 29883
CANONICAL_TARGETS = (
    "D01_CEREBRO_ROOT",
    "D02_CONFESION_ECLESIAL_REFORMADA",
    "D02_MULTI_INTERDISCIPLINAR",
    "D02_ORQUESTADOR",
    "D03_TRANSCRIPCION_ROOT",
    "D04_HERMENEUTICA_HG",
    "D04_TRADUCCION_LENGUAS_ANTIGUAS",
    "D04_TRADUCCION_GENERAL",
    "D05_CALIBRE",
    "D05_DOCLING",
    "D06_ANTI_ALUCINACIONES",
    "D06_ANALISIS_AVANZADO",
    "D06_ARCHIVADO_DETECCION",
    "D06_COGNITIVE_CI_CD",
    "D06_CONSOLA",
    "D06_MEMORIA_GOBERNADA",
    "D06_MIGRACION_PERSISTENCIA",
    "D06_MOTOR_PROTOCOLAR",
    "D06_PORTABILIDAD_BASE",
    "D06_RUNTIME_ANDROID_WINDOWS",
    "D06_TESTING",
)
MODEL_TARGETS = {
    "D01_CEREBRO_ROOT",
    "D03_TRANSCRIPCION_ROOT",
    "D04_TRADUCCION_GENERAL",
    "D05_DOCLING",
    "D06_ANALISIS_AVANZADO",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def git_head(root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def record(target_id: str, operation: str, status: str, *, exit_code: int, detail: dict, reason: str = "") -> dict:
    body = {
        "target_id": target_id,
        "operation": operation,
        "status": status,
        "exit_code": exit_code,
        "reason": reason,
        "detail": detail,
        "worker_certification": "NOT_GRANTED",
    }
    body["output_sha256"] = sha256_bytes(canonical(body["detail"]))
    return body


def _copy_exec(binary: Path) -> tuple[tempfile.TemporaryDirectory, Path]:
    temp = tempfile.TemporaryDirectory(prefix="louksna1-exec-")
    dest = Path(temp.name) / binary.name
    payload = binary.read_bytes()
    dest.write_bytes(payload)
    os.chmod(dest, 0o755)
    if dest.read_bytes() != payload:
        temp.cleanup()
        raise RuntimeError("EXECUTABLE_COPY_MUTATED")
    return temp, dest


def op_confession(runtime: Path) -> dict:
    target = "D02_CONFESION_ECLESIAL_REFORMADA"
    db = runtime / "2. Orquestación" / "Confesión Eclesial Reformada" / "Biblia Textual BTX -- Biblia Textual BTX -- ( WeLib.org ).sqlite3"
    if db.is_symlink() or not db.is_file():
        return record(target, "read_genesis_1_1", "FAIL", exit_code=2, detail={}, reason="BIBLE_DATABASE_MISSING")
    uri = "file:" + quote(str(db.resolve()), safe="/") + "?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as conn:
        quick = [row[0] for row in conn.execute("PRAGMA quick_check")]
        text = conn.execute(
            "SELECT text FROM verses WHERE book_id=1 AND chapter_number=1 AND verse_number=1 AND verse_suffix=''"
        ).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    ok = quick == ["ok"] and text and text[0] == GENESIS_1_1 and count == VERSE_COUNT
    return record(
        target,
        "read_genesis_1_1",
        "PASS" if ok else "FAIL",
        exit_code=0 if ok else 4,
        detail={"quick_check": quick, "verse_sha256": sha256_bytes((text[0] if text else "").encode()), "verse_count": count, "database_sha256": sha256_file(db), "write_access": False},
        reason="" if ok else "BIBLE_CONTENT_OR_INTEGRITY_MISMATCH",
    )


def op_orchestrator(runtime: Path) -> dict:
    target = "D02_ORQUESTADOR"
    entry = runtime / "2. Orquestación" / "Orquestador" / "CLIs" / "cli_registry.py"
    manifest = runtime / "2. Orquestación" / "Orquestador" / "punto.json"
    contract = runtime / "2. Orquestación" / "Orquestador" / "CLIs" / "cli_contract.json"
    if any(path.is_symlink() or not path.is_file() for path in (entry, manifest, contract)):
        return record(target, "audit_cli_registry", "FAIL", exit_code=2, detail={}, reason="CLI_REGISTRY_MISSING")
    spec = importlib.util.spec_from_file_location("louksna1_cli_registry", entry)
    if spec is None or spec.loader is None:
        return record(target, "audit_cli_registry", "FAIL", exit_code=2, detail={}, reason="CLI_REGISTRY_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.selftest(manifest, contract)
    ok = result.get("status") == "PASS" and result.get("domain_count") == 8 and result.get("all_adapters_present") is True and result.get("side_effects") is False
    return record(target, "audit_cli_registry", "PASS" if ok else "FAIL", exit_code=0 if ok else 4, detail={"registry": result}, reason="" if ok else "CLI_REGISTRY_SELFTEST_NOT_PASS")


def op_multi(runtime: Path, repo: Path) -> dict:
    target = "D02_MULTI_INTERDISCIPLINAR"
    entry = runtime / "2. Orquestación" / "Multi + Interdisciplinar" / "cajita_axiom_source_loader.py"
    companion = repo / "Louksna1.md"
    if entry.is_symlink() or not entry.is_file() or companion.is_symlink() or not companion.is_file():
        return record(target, "verify_axiom_source_binding", "FAIL", exit_code=2, detail={}, reason="AXIOM_BINDING_INPUT_MISSING")
    spec = importlib.util.spec_from_file_location("louksna1_axiom_loader", entry)
    if spec is None or spec.loader is None:
        return record(target, "verify_axiom_source_binding", "FAIL", exit_code=2, detail={}, reason="AXIOM_LOADER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        result = module.verify_binding(runtime, companion)
    except Exception as exc:
        return record(target, "verify_axiom_source_binding", "FAIL", exit_code=4, detail={"error": type(exc).__name__}, reason=str(exc)[:240])
    ok = result.get("status") == "PASS_SOURCE_PREFIX_VERIFIED" and result.get("certification") == "NOT_GRANTED"
    public = {key: result.get(key) for key in ("status", "companion_sha256", "protected_prefix_sha256", "protected_prefix_bytes", "framework_count", "semantic_graph_execution", "certification")}
    return record(target, "verify_axiom_source_binding", "PASS" if ok else "FAIL", exit_code=0 if ok else 4, detail=public, reason="" if ok else "AXIOM_BINDING_NOT_PASS")


def op_quickjs(runtime: Path) -> dict:
    target = "D06_CONSOLA"
    binary = runtime / "6. Sistema Inteligente" / "Consola" / "quickjs-linux-x86_64-2026-06-04" / "qjs"
    if binary.is_symlink() or not binary.is_file():
        return record(target, "evaluate_fixed_javascript_fixture", "FAIL", exit_code=2, detail={}, reason="QUICKJS_BINARY_MISSING")
    before = binary.read_bytes()
    mode = binary.stat().st_mode
    temp, exe = _copy_exec(binary)
    try:
        proc = subprocess.run([str(exe), "--std", "-e", 'print(JSON.stringify({answer:2+2,strict:true}))'], capture_output=True, text=True, timeout=8, check=False)
    finally:
        unchanged = binary.read_bytes() == before and binary.stat().st_mode == mode
        temp.cleanup()
    try:
        parsed = json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        parsed = None
    ok = proc.returncode == 0 and parsed == {"answer": 4, "strict": True} and unchanged
    return record(target, "evaluate_fixed_javascript_fixture", "PASS" if ok else "FAIL", exit_code=0 if ok else 4, detail={"stdout_sha256": sha256_bytes(proc.stdout.encode()), "return_code": proc.returncode, "source_bytes_unchanged": unchanged, "binary_sha256": sha256_bytes(before)}, reason="" if ok else "QUICKJS_KNOWN_ANSWER_FAILED")


def op_siegfried(runtime: Path) -> dict:
    target = "D06_ARCHIVADO_DETECCION"
    binary = runtime / "6. Sistema Inteligente" / "Archivado Deteccion" / "siegfried_1-11-6_linux-x86_64_static" / "sf"
    if binary.is_symlink() or not binary.is_file():
        return record(target, "identify_png_signature", "FAIL", exit_code=2, detail={}, reason="SIEGFRIED_BINARY_MISSING")
    payload = b"\x89PNG\r\n\x1a\n" + b"louksna1-signature-fixture"
    temp, exe = _copy_exec(binary)
    try:
        with tempfile.NamedTemporaryFile(prefix="louksna1-png-", delete=False) as handle:
            handle.write(payload)
            sample = Path(handle.name)
        proc = subprocess.run([str(exe), "-json", str(sample)], capture_output=True, text=True, timeout=20, check=False)
    finally:
        temp.cleanup()
        sample.unlink(missing_ok=True)
    identified = "png" in proc.stdout.casefold() or "image/png" in proc.stdout.casefold()
    ok = proc.returncode == 0 and identified
    return record(target, "identify_png_signature", "PASS" if ok else "FAIL", exit_code=0 if ok else 4, detail={"return_code": proc.returncode, "identified_png": identified, "stdout_sha256": sha256_bytes(proc.stdout.encode()), "stderr_sha256": sha256_bytes(proc.stderr.encode()), "binary_sha256": sha256_file(binary)}, reason="" if ok else proc.stderr[-240] or "SIEGFRIED_IDENTIFICATION_FAILED")


def op_opa(repo: Path) -> dict:
    target = "D06_COGNITIVE_CI_CD"
    binary = repo / "externalized-assets-staging" / "6-Sistema-Inteligente" / "Cognitive-CI-CD" / "opa_linux_amd64_static"
    if binary.is_symlink() or not binary.is_file():
        return record(target, "evaluate_policy", "FAIL", exit_code=2, detail={}, reason="OPA_BINARY_MISSING")
    temp, exe = _copy_exec(binary)
    try:
        policy = Path(temp.name) / "policy.rego"
        payload = Path(temp.name) / "input.json"
        policy.write_text("package louksna1\nallow if {\n  input.answer == 4\n}\n", encoding="utf-8")
        payload.write_text('{"answer":4}\n', encoding="utf-8")
        proc = subprocess.run([str(exe), "eval", "-d", str(policy), "-i", str(payload), "data.louksna1.allow"], capture_output=True, text=True, timeout=20, check=False)
    finally:
        temp.cleanup()
    allowed = '"value":true' in proc.stdout.replace(" ", "")
    ok = proc.returncode == 0 and allowed
    return record(target, "evaluate_policy", "PASS" if ok else "FAIL", exit_code=0 if ok else 4, detail={"return_code": proc.returncode, "stdout_sha256": sha256_bytes(proc.stdout.encode()), "stderr_tail": proc.stderr[-240:], "binary_sha256": sha256_file(binary)}, reason="" if ok else "OPA_POLICY_KNOWN_ANSWER_FAILED")


def op_sml(runtime: Path) -> dict:
    target = "D06_MOTOR_PROTOCOLAR"
    header = runtime / "6. Sistema Inteligente" / "Motor - Protocolar" / "sml-1.2.0" / "sml-1.2.0" / "include" / "boost" / "sml.hpp"
    if header.is_symlink() or not header.is_file():
        return record(target, "protocol_transitions", "FAIL", exit_code=2, detail={}, reason="SML_HEADER_MISSING")
    include = header.parents[1]
    with tempfile.TemporaryDirectory(prefix="louksna1-sml-") as temp_name:
        source = Path(temp_name) / "protocol.cpp"
        binary = Path(temp_name) / "protocol"
        source.write_text('#include <boost/sml.hpp>\n#include <iostream>\nstruct idle_state {}; struct active_state {}; struct done_state {}; struct start_event {}; struct stop_event {}; struct protocol { auto operator()() const { using namespace boost::sml; return make_transition_table(*state<idle_state> + event<start_event> = state<active_state>, state<active_state> + event<stop_event> = state<done_state>); } }; int main(){ boost::sml::sm<protocol> sm; if(!sm.is(boost::sml::state<idle_state>)) return 11; sm.process_event(start_event{}); if(!sm.is(boost::sml::state<active_state>)) return 12; sm.process_event(stop_event{}); if(!sm.is(boost::sml::state<done_state>)) return 13; std::cout << "idle>active>done\\n"; return 0; }\n', encoding="utf-8")
        build = subprocess.run(["g++", "-std=c++17", "-O2", "-I", str(include), str(source), "-o", str(binary)], capture_output=True, text=True, timeout=90, check=False)
        if build.returncode != 0:
            return record(target, "protocol_transitions", "FAIL", exit_code=4, detail={"stderr_tail": build.stderr[-400:]}, reason="SML_COMPILE_FAILED")
        proc = subprocess.run([str(binary)], capture_output=True, text=True, timeout=8, check=False)
    ok = proc.returncode == 0 and proc.stdout.strip() == "idle>active>done"
    return record(target, "protocol_transitions", "PASS" if ok else "FAIL", exit_code=0 if ok else 4, detail={"known_answer": proc.stdout.strip(), "header_sha256": sha256_file(header)}, reason="" if ok else "SML_TRANSITION_MISMATCH")


def op_sqlite(runtime: Path) -> dict:
    target = "D06_MEMORIA_GOBERNADA"
    root = runtime / "6. Sistema Inteligente" / "Memoria Gobernada" / "sqlite-amalgamation-3530400" / "sqlite-amalgamation-3530400"
    sources = [root / "shell.c", root / "sqlite3.c", root / "sqlite3.h"]
    if any(path.is_symlink() or not path.is_file() for path in sources):
        return record(target, "sqlite_roundtrip", "FAIL", exit_code=2, detail={}, reason="SQLITE_AMALGAMATION_MISSING")
    with tempfile.TemporaryDirectory(prefix="louksna1-sqlite-") as temp_name:
        temp = Path(temp_name)
        binary = temp / "sqlite3"
        build = subprocess.run(["cc", "-O2", "-DSQLITE_THREADSAFE=1", str(sources[0]), str(sources[1]), "-ldl", "-lpthread", "-lm", "-o", str(binary)], capture_output=True, text=True, timeout=180, check=False)
        if build.returncode != 0:
            return record(target, "sqlite_roundtrip", "FAIL", exit_code=4, detail={"stderr_tail": build.stderr[-400:]}, reason="SQLITE_COMPILE_FAILED")
        provenance = sha256_bytes(b"CAJITA_D06_MEMORIA_GOBERNADA_ROUNDTRIP_FIXTURE_V1")
        sql = "CREATE TABLE memory_records(key TEXT PRIMARY KEY,value TEXT NOT NULL,provenance_sha256 TEXT NOT NULL); BEGIN IMMEDIATE; INSERT INTO memory_records VALUES('smoke-key','smoke-value','" + provenance + "'); COMMIT; SELECT key||'|'||value||'|'||provenance_sha256 FROM memory_records WHERE key='smoke-key'; PRAGMA integrity_check;"
        proc = subprocess.run([str(binary), "-batch", "-bail", "-noheader", str(temp / "memory.sqlite3")], input=sql, capture_output=True, text=True, timeout=15, check=False)
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    expected = ["smoke-key|smoke-value|" + provenance, "ok"]
    ok = proc.returncode == 0 and lines == expected
    return record(target, "sqlite_roundtrip", "PASS" if ok else "FAIL", exit_code=0 if ok else 4, detail={"lines": lines, "return_code": proc.returncode}, reason="" if ok else "SQLITE_ROUNDTRIP_MISMATCH")


def op_not_executable(target_id: str, operation: str, reason: str) -> dict:
    return record(target_id, operation, "FAIL", exit_code=2, detail={"executed": False}, reason=reason)


def run_matrix(repo: Path) -> list[dict]:
    runtime = repo / "cajita-luna-runtime"
    blocked = {
        "D01_CEREBRO_ROOT": ("generate_text", "REFERENCE_MODEL_EQUIVALENCE_NOT_EXECUTED"),
        "D03_TRANSCRIPCION_ROOT": ("transcribe_audio", "REFERENCE_TRANSCRIPT_EQUIVALENCE_NOT_EXECUTED"),
        "D04_TRADUCCION_GENERAL": ("translate_text", "REFERENCE_TRANSLATION_EQUIVALENCE_NOT_EXECUTED"),
        "D05_CALIBRE": ("convert_document", "CALIBRE_BINARY_NOT_EXECUTED"),
        "D05_DOCLING": ("extract_document_image", "REFERENCE_EXTRACTION_EQUIVALENCE_NOT_EXECUTED"),
        "D06_ANTI_ALUCINACIONES": ("score_grounding", "ONNX_GROUNDING_OPERATION_NOT_EXECUTED"),
        "D06_ANALISIS_AVANZADO": ("analyze_reasoning", "REFERENCE_REASONING_EQUIVALENCE_NOT_EXECUTED"),
        "D06_PORTABILIDAD_BASE": ("host_matrix", "WINDOWS_CMAKE_HOST_NOT_EXECUTED"),
        "D06_RUNTIME_ANDROID_WINDOWS": ("native_host_matrix", "ANDROID_WINDOWS_NATIVE_HOSTS_NOT_EXECUTED"),
    }
    rows = []
    for target_id in CANONICAL_TARGETS:
        if target_id == "D02_CONFESION_ECLESIAL_REFORMADA":
            rows.append(op_confession(runtime))
        elif target_id == "D02_ORQUESTADOR":
            rows.append(op_orchestrator(runtime))
        elif target_id == "D02_MULTI_INTERDISCIPLINAR":
            rows.append(op_multi(runtime, repo))
        elif target_id == "D06_CONSOLA":
            rows.append(op_quickjs(runtime))
        elif target_id == "D06_ARCHIVADO_DETECCION":
            rows.append(op_siegfried(runtime))
        elif target_id == "D06_COGNITIVE_CI_CD":
            rows.append(op_opa(repo))
        elif target_id == "D06_MEMORIA_GOBERNADA":
            rows.append(op_sqlite(runtime))
        elif target_id == "D06_MOTOR_PROTOCOLAR":
            rows.append(op_sml(runtime))
        elif target_id == "D06_MIGRACION_PERSISTENCIA":
            rows.append(op_rqlite(repo))
        elif target_id == "D06_TESTING":
            rows.append(op_pytest(runtime))
        elif target_id == "D04_HERMENEUTICA_HG":
            rows.append(op_trealla(runtime))
        elif target_id == "D04_TRADUCCION_LENGUAS_ANTIGUAS":
            rows.append(op_foma(runtime))
        else:
            operation, reason = blocked[target_id]
            rows.append(op_not_executable(target_id, operation, reason))
    return rows


def op_rqlite(repo: Path) -> dict:
    target = "D06_MIGRACION_PERSISTENCIA"
    archive = repo / "externalized-assets-staging" / "6-Sistema-Inteligente" / "Migracion-y-Persistencia" / "rqlite-v10.2.7-linux-amd64.tar.gz"
    if archive.is_symlink() or not archive.is_file():
        return record(target, "apply_migration", "FAIL", exit_code=2, detail={}, reason="RQLITE_ARCHIVE_MISSING")
    with tempfile.TemporaryDirectory(prefix="louksna1-rqlite-") as temp_name:
        temp = Path(temp_name)
        with tarfile.open(archive, "r:gz") as bundle:
            bundle.extractall(temp)
        server = next(temp.rglob("rqlited"))
        client = next(temp.rglob("rqlite"))
        os.chmod(server, 0o755)
        os.chmod(client, 0o755)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            http_port = probe.getsockname()[1]
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            raft_port = probe.getsockname()[1]
        data = temp / "data"
        log_path = temp / "rqlited.log"
        log_file = log_path.open("w", encoding="utf-8")
        proc = subprocess.Popen(
            [str(server), "-http-addr", f"127.0.0.1:{http_port}", "-raft-addr", f"127.0.0.1:{raft_port}", str(data)],
            stdout=log_file, stderr=subprocess.STDOUT, text=True,
        )
        try:
            leader = False
            deadline = time.time() + 20
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                try:
                    with urlopen(f"http://127.0.0.1:{http_port}/status", timeout=1) as resp:
                        status = json.loads(resp.read().decode())
                    raft = status.get("store", {}).get("raft", {})
                    leader_info = status.get("store", {}).get("leader", {})
                    if raft.get("state") == "Leader" and leader_info.get("node_id"):
                        leader = True
                        break
                except (OSError, json.JSONDecodeError, ValueError):
                    pass
                time.sleep(0.25)
            if not leader:
                log_file.flush()
                tail = log_path.read_text(encoding="utf-8", errors="replace")[-300:]
                return record(target, "apply_migration", "FAIL", exit_code=4, detail={"stderr_tail": tail}, reason="RQLITE_LEADER_NOT_ELECTED")
            version = sha256_bytes(b"LOUKSNA1_MIGRATION_V1")
            sql = "\n".join([
                "CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_sha256 TEXT NOT NULL);",
                f"INSERT INTO schema_migrations(version, applied_sha256) VALUES(1, '{version}');",
                "SELECT version, applied_sha256 FROM schema_migrations;",
            ]) + "\n"
            cli = subprocess.run(
                [str(client), "-H", "127.0.0.1", "-p", str(http_port)],
                input=sql, capture_output=True, text=True, timeout=20, check=False,
            )
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            log_file.close()
    ok = cli.returncode == 0 and "ERR!" not in cli.stdout and "1 row affected" in cli.stdout and version in cli.stdout
    return record(
        target,
        "apply_migration",
        "PASS" if ok else "FAIL",
        exit_code=0 if ok else 4,
        detail={
            "cli_rc": cli.returncode,
            "query_sha256": sha256_bytes(cli.stdout.encode()),
            "query_contains_migration_sha256": version in cli.stdout,
            "server_version_banner": "v10.2.7" in cli.stdout,
            "archive_sha256": sha256_file(archive),
        },
        reason="" if ok else "RQLITE_MIGRATION_MISMATCH",
    )


def op_pytest(runtime: Path) -> dict:
    target = "D06_TESTING"
    wheel = runtime / "6. Sistema Inteligente" / "Testing" / "pytest-9.1.1-py3-none-any.rebuilt.whl"
    crate = runtime / "6. Sistema Inteligente" / "Testing" / "criterion-0.8.2.crate"
    if wheel.is_symlink() or not wheel.is_file() or crate.is_symlink() or not crate.is_file():
        return record(target, "run_pinned_pytest", "FAIL", exit_code=2, detail={}, reason="PYTEST_OR_CRITERION_MISSING")
    with tempfile.TemporaryDirectory(prefix="louksna1-pytest-") as temp_name:
        temp = Path(temp_name)
        target_dir = temp / "deps"
        install = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir", "--target", str(target_dir), str(wheel), "py==1.11.0"],
            capture_output=True, text=True, timeout=180, check=False,
        )
        if install.returncode != 0:
            return record(target, "run_pinned_pytest", "FAIL", exit_code=4, detail={"return_code": install.returncode, "stderr_tail": install.stderr[-400:], "wheel_sha256": sha256_file(wheel)}, reason="PINNED_PYTEST_INSTALL_FAILED")
        installed = sorted(path.name for path in target_dir.glob("*.dist-info"))
        test = temp / "test_criterion_crate.py"
        test.write_text(
            "import tarfile\nfrom pathlib import Path\nCRATE = Path(%r)\n"
            "def test_criterion_crate_contains_manifest():\n"
            "    assert CRATE.stat().st_size > 0\n"
            "    with tarfile.open(CRATE, 'r:gz') as bundle:\n"
            "        names = bundle.getnames()\n"
            "    assert any(name.endswith('Cargo.toml') for name in names)\n" % str(crate),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(target_dir)
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", str(test), "--noconftest"], cwd=temp, env=env, capture_output=True, text=True, timeout=60, check=False)
    ok = proc.returncode == 0 and "1 passed" in proc.stdout
    return record(
        target,
        "run_pinned_pytest",
        "PASS" if ok else "FAIL",
        exit_code=0 if ok else 4,
        detail={
            "return_code": proc.returncode,
            "stdout_tail": proc.stdout[-300:],
            "stderr_tail": proc.stderr[-300:],
            "installed_dist_info": installed,
            "wheel_sha256": sha256_file(wheel),
            "crate_sha256": sha256_file(crate),
        },
        reason="" if ok else "PINNED_PYTEST_SUITE_FAILED",
    )


def op_trealla(runtime: Path) -> dict:
    target = "D04_HERMENEUTICA_HG"
    source = runtime / "4. Traductor Inteligente" / "Hermenéutica H-G" / "trealla-2.100.24" / "trealla-2.100.24"
    if (source / "Makefile").is_symlink() or not (source / "Makefile").is_file():
        return record(target, "interpret_fixture", "FAIL", exit_code=2, detail={}, reason="TREALLA_SOURCE_MISSING")
    with tempfile.TemporaryDirectory(prefix="louksna1-trealla-") as temp_name:
        dest = Path(temp_name) / "trealla"
        shutil.copytree(source, dest, symlinks=False)
        readme = dest / "README.md"
        readme_stub = False
        if not readme.is_file():
            readme.write_text("Vendored snapshot omitted README.md. This file only satisfies the Makefile prerequisite.\n", encoding="utf-8")
            readme_stub = True
        build = subprocess.run(
            ["make", "-j", str(os.cpu_count() or 1), "NOFFI=1", "NOSSL=1", "ISOCLINE=1", "CC=cc"],
            cwd=dest, capture_output=True, text=True, timeout=240, check=False,
        )
        binary = dest / "tpl"
        if build.returncode != 0 or not binary.is_file():
            return record(target, "interpret_fixture", "FAIL", exit_code=4, detail={"return_code": build.returncode, "stderr_tail": build.stderr[-400:], "readme_stub": readme_stub}, reason="TREALLA_BUILD_FAILED")
        os.chmod(binary, 0o755)
        proc = subprocess.run([str(binary), "-g", "X is 2+2, write(X), nl, halt."], capture_output=True, text=True, timeout=20, check=False)
    ok = proc.returncode == 0 and proc.stdout.strip() == "4"
    return record(
        target,
        "interpret_fixture",
        "PASS" if ok else "FAIL",
        exit_code=0 if ok else 4,
        detail={
            "return_code": proc.returncode,
            "stdout": proc.stdout.strip()[:80],
            "build_flags": ["NOFFI=1", "NOSSL=1", "ISOCLINE=1"],
            "readme_stub": readme_stub,
            "source_makefile_sha256": sha256_file(source / "Makefile"),
        },
        reason="" if ok else "TREALLA_KNOWN_ANSWER_MISMATCH",
    )


def op_foma(runtime: Path) -> dict:
    target = "D04_TRADUCCION_LENGUAS_ANTIGUAS"
    source = runtime / "4. Traductor Inteligente" / "Traducción de lenguas antiguas" / "foma-master" / "foma-master" / "foma"
    if (source / "Makefile").is_symlink() or not (source / "Makefile").is_file():
        return record(target, "analyze_morphology", "FAIL", exit_code=2, detail={}, reason="FOMA_SOURCE_MISSING")
    missing = [name for name in ("flex", "bison", "m4") if shutil.which(name) is None]
    if missing:
        return record(target, "analyze_morphology", "FAIL", exit_code=2, detail={"missing_tools": missing}, reason="FOMA_BUILD_TOOLS_MISSING")
    with tempfile.TemporaryDirectory(prefix="louksna1-foma-") as temp_name:
        dest = Path(temp_name) / "foma"
        shutil.copytree(source, dest, symlinks=False)
        build = subprocess.run(
            ["make", "-j", str(os.cpu_count() or 1), "foma"],
            cwd=dest, capture_output=True, text=True, timeout=240, check=False,
        )
        binary = dest / "foma"
        if build.returncode != 0 or not binary.is_file():
            return record(target, "analyze_morphology", "FAIL", exit_code=4, detail={"return_code": build.returncode, "stderr_tail": (build.stderr or "")[-400:]}, reason="FOMA_BUILD_FAILED")
        os.chmod(binary, 0o755)
        proc = subprocess.run(
            [str(binary), "-q", "-r", "-e", "regex a -> b ;", "-e", "apply down a", "-s"],
            capture_output=True, text=True, timeout=20, check=False,
        )
    ok = proc.returncode == 0 and proc.stdout.strip() == "b"
    return record(
        target,
        "analyze_morphology",
        "PASS" if ok else "FAIL",
        exit_code=0 if ok else 4,
        detail={
            "return_code": proc.returncode,
            "stdout": proc.stdout.strip()[:80],
            "rule": "a -> b",
            "input": "a",
            "expected": "b",
            "source_makefile_sha256": sha256_file(source / "Makefile"),
        },
        reason="" if ok else "FOMA_REWRITE_MISMATCH",
    )


def measured_resources(repo: Path) -> dict:
    try:
        pages = os.sysconf("SC_AVPHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        ram = int(pages) * int(page_size)
    except (OSError, ValueError):
        ram = None
    disk = shutil.disk_usage(repo).free
    return {
        "ram_available_bytes": ram,
        "disk_available_bytes": disk,
        "cpu_count": os.cpu_count(),
        "platform": platform.platform(),
        "offline_env": {"HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE"), "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE")},
        "confidence": "MEASURED" if ram is not None and disk is not None and os.cpu_count() else "UNKNOWN",
    }


def rollback_probe(runtime: Path) -> dict:
    """Restore an executed binary copy. This is not a product-update rollback."""
    binary = runtime / "6. Sistema Inteligente" / "Consola" / "quickjs-linux-x86_64-2026-06-04" / "qjs"
    if not binary.is_file():
        return {"status": "FAIL", "scope": "NOT_RUN", "reason": "ROLLBACK_SOURCE_MISSING"}
    original = binary.read_bytes()
    with tempfile.TemporaryDirectory(prefix="louksna1-rollback-") as temp_name:
        work = Path(temp_name) / "qjs"
        checkpoint = Path(temp_name) / "qjs.checkpoint"
        work.write_bytes(original)
        checkpoint.write_bytes(original)
        work.write_bytes(original + b"TAMPER")
        if work.read_bytes() == original:
            return {"status": "FAIL", "scope": "EXECUTED_ARTIFACT_COPY", "reason": "TAMPER_DID_NOT_CHANGE_BYTES"}
        work.write_bytes(checkpoint.read_bytes())
        restored = work.read_bytes() == original and sha256_file(work) == sha256_bytes(original)
        os.chmod(work, 0o755)
        proc = subprocess.run([str(work), "--std", "-e", "print(2+2)"], capture_output=True, text=True, timeout=8, check=False)
    ok = restored and proc.returncode == 0 and proc.stdout.strip() == "4"
    return {
        "status": "PASS" if ok else "FAIL",
        "scope": "EXECUTED_ARTIFACT_COPY_NOT_PRODUCT_UPDATE",
        "restored_hash_match": restored,
        "post_restore_exit_code": proc.returncode,
        "reason": "" if ok else "ROLLBACK_POST_RESTORE_EXECUTION_FAILED",
    }


def identity_report(repo: Path) -> dict:
    manifest_path = repo / "cajita-luna-runtime" / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
    workflow = repo / ".github" / "workflows" / "cajita-louksna1-factory.yml"
    adapter = repo / "cajita-luna-runtime" / "cajita_task_adapters.py"
    problems = []
    candidate = None
    if manifest_path.is_file():
        candidate = json.loads(manifest_path.read_text(encoding="utf-8")).get("candidate_id")
        if candidate != CANDIDATE_ID:
            problems.append("WEIGHT_MANIFEST_CANDIDATE_MISMATCH")
    else:
        problems.append("WEIGHT_MANIFEST_MISSING")
    workflow_text = workflow.read_text(encoding="utf-8") if workflow.is_file() else ""
    if not workflow_text.startswith("name: " + WORKFLOW_NAME + "\n"):
        problems.append("FACTORY_WORKFLOW_NAME_DOES_NOT_MATCH_PACKAGED_CANDIDATE")
    adapter_text = adapter.read_text(encoding="utf-8") if adapter.is_file() else ""
    if f'CANDIDATE_ID = "{CANDIDATE_ID}"' not in adapter_text:
        problems.append("ADAPTER_CANDIDATE_ID_MISMATCH")
    return {"status": "PASS" if not problems else "FAIL", "candidate_id": candidate, "workflow_name": WORKFLOW_NAME, "problems": problems}


def provenance_report(repo: Path, head: str) -> dict:
    path = repo / "docs" / "cajita-luna" / "LOUKSNA1_RELEASE_MANIFEST.json"
    if not path.is_file():
        return {"status": "FAIL", "reason": "RELEASE_MANIFEST_MISSING"}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    if manifest.get("source_commit") != head:
        problems.append("PUBLISHED_MANIFEST_SOURCE_COMMIT_DIFFERS_FROM_EXECUTION_HEAD")
    louksna = repo / "Louksna1.md"
    if louksna.is_file() and sha256_file(louksna) != manifest.get("louksna1", {}).get("sha256"):
        problems.append("LOUKSNA1_HASH_DIFFERS_FROM_PUBLISHED_MANIFEST")
    protected = repo / "LOUKSNAMEJORADA.md"
    if protected.is_file():
        if sha256_file(protected) != manifest.get("protected_architecture", {}).get("sha256"):
            problems.append("PROTECTED_ARCHITECTURE_HASH_MISMATCH")
    else:
        problems.append("PROTECTED_ARCHITECTURE_NOT_CHECKED_IN_THIS_EXECUTION")
    if manifest.get("global_certification") == "GRANTED":
        problems.append("STALE_MANIFEST_ALREADY_CLAIMS_GRANT")
    return {"status": "PASS" if not problems else "FAIL", "published_source_commit": manifest.get("source_commit"), "execution_head": head, "problems": problems}


def decide(matrix: list[dict], identity: dict, resources: dict, rollback: dict, provenance: dict, *, worker_claim: str, axiom_established: bool = False) -> dict:
    by_id = {row["target_id"]: row for row in matrix}
    missing = [target for target in CANONICAL_TARGETS if target not in by_id]
    passed = [target for target in CANONICAL_TARGETS if by_id.get(target, {}).get("status") == "PASS" and by_id.get(target, {}).get("exit_code") == 0]
    coverage = "PASS" if not missing and len(passed) == 21 else "FAIL"
    semantic = "PASS" if all(by_id.get(target, {}).get("detail", {}).get("reference_kind") == "AUTHORIZED_REFERENCE_MODEL" for target in MODEL_TARGETS) else "FAIL"
    axiom = "PASS" if axiom_established else "FAIL"
    host = "PASS" if resources.get("confidence") == "MEASURED" and resources.get("platform", "").casefold().find("android") >= 0 else "FAIL"
    host_reason = "LINUX_RESOURCE_MEASUREMENT_IS_NOT_THE_DECLARED_ANDROID_WINDOWS_MATRIX" if host == "FAIL" else ""
    rollback_ok = rollback.get("status") == "PASS" and rollback.get("scope") == "PRODUCT_CANDIDATE_UPDATE"
    independence = worker_claim == "NOT_GRANTED"
    gates = {
        "identity": {"status": identity.get("status", "FAIL"), "problems": identity.get("problems", [])},
        "coverage_21": {"status": coverage, "passed": passed, "failed": [target for target in CANONICAL_TARGETS if target not in passed]},
        "semantic_quality": {"status": semantic, "reason": "NO_AUTHORIZED_REFERENCE_MODEL_COMPARISON"},
        "axiom_semantics": {"status": axiom, "reason": "PROPOSITION_VALIDITY_AND_LOGICAL_CONSISTENCY_NOT_ESTABLISHED"},
        "host_resources": {"status": host, "reason": host_reason, "measurement": resources},
        "rollback": {"status": "PASS" if rollback_ok else "FAIL", "observed": rollback},
        "provenance": {"status": provenance.get("status", "FAIL"), "problems": provenance.get("problems", [])},
        "independence": {"status": "PASS" if independence else "FAIL", "worker_claim": worker_claim, "evaluator": EVALUATOR_ID, "worker": WORKER_ID},
        "baseline_integrity": {"status": "FAIL" if "PROTECTED_ARCHITECTURE_HASH_MISMATCH" in provenance.get("problems", []) or "PROTECTED_ARCHITECTURE_NOT_CHECKED_IN_THIS_EXECUTION" in provenance.get("problems", []) else "PASS"},
    }
    granted = all(gate["status"] == "PASS" for gate in gates.values())
    return {
        "schema": SCHEMA,
        "decision": "GRANTED" if granted else "NOT_GRANTED",
        "global_certification": "GRANTED" if granted else "NOT_GRANTED",
        "authority": "INDEPENDENT_VALIDATOR_NOT_SELF_CERTIFICATION",
        "gates": gates,
        "target_adapter_registration": {
            "canonical_target_count": 21,
            "all_21_target_task_adapters": "ESTABLISHED" if coverage == "PASS" else "NOT_ESTABLISHED",
        },
        "semantic_gates": {
            "model_quality_equivalence": "ESTABLISHED" if semantic == "PASS" else "NOT_ESTABLISHED",
            "axiom_proposition_validity": "ESTABLISHED" if axiom == "PASS" else "NOT_ESTABLISHED",
            "semantic_consistency": "ESTABLISHED" if axiom == "PASS" else "NOT_ESTABLISHED",
            "full_integrated_runtime_behaviour": "ESTABLISHED" if granted else "NOT_ESTABLISHED",
        },
    }


def load_custosz(pyz: Path):
    if pyz.is_symlink() or not pyz.is_file():
        raise RuntimeError("CUSTOSZ_PYZ_MISSING")
    if sha256_file(pyz) != CUSTOSZ_SHA256:
        raise RuntimeError("CUSTOSZ_PYZ_HASH_MISMATCH")
    sys.path.insert(0, str(pyz))
    from custoszv9.crfu.coordinator import run_bounded_mission
    from custoszv9.crfu.model import TaskContract
    from custoszv9.crfu.planner import ActionSpec
    from custoszv9.crfu.resources import probe_host_resources
    # The pinned coordinator reads task.source_state_hash, but the validated
    # contract exposes that field only through task.value. The pyz bytes stay
    # unchanged; this binds the missing property to the already validated field.
    if not isinstance(getattr(TaskContract, "source_state_hash", None), property):
        TaskContract.source_state_hash = property(lambda self: str(self.value["source_state_hash"]))
    return run_bounded_mission, ActionSpec, probe_host_resources


def authorize(task: dict) -> dict:
    """Scope-bound execution authority. It cannot certify the product."""
    if task.get("task_id") != "louksna1-integral-certification":
        return {"status": "FAIL", "task_id": task.get("task_id")}
    if "SELF_CERTIFICATION" not in task.get("permitted_effects", []) and "NO_SELF_CERTIFICATION" not in task.get("preconditions", []):
        return {"status": "FAIL", "task_id": task.get("task_id")}
    if task.get("authorized_scope") != "EXECUTE_LOUKSNA1_INTEGRAL_MISSION_ISSUE_110":
        return {"status": "FAIL", "task_id": task.get("task_id")}
    return {"status": "PASS", "task_id": task["task_id"], "authorizes_certification": False}


def build_task(head: str) -> dict:
    return {
        "task_id": "louksna1-integral-certification",
        "mission_id": "issue-110",
        "project_id": "louksna1",
        "source_identity": WORKER_ID,
        "target_identity": CANDIDATE_ID,
        "source_state_hash": sha256_bytes(head.encode()),
        "dependency_set": ["issue-110"],
        "authorized_scope": "EXECUTE_LOUKSNA1_INTEGRAL_MISSION_ISSUE_110",
        "required_capabilities": ["execute_consumer_matrix"],
        "inputs": ["repository"],
        "preconditions": ["NO_SELF_CERTIFICATION", "FAIL_CLOSED"],
        "permitted_effects": ["WRITE_EVIDENCE"],
        "resource_budget": {"ram_required_bytes": 64 * 1024 * 1024, "ram_reserved_bytes": 32 * 1024 * 1024, "disk_required_bytes": 64 * 1024 * 1024, "max_concurrency": 1},
        "execution_deadline": "2026-12-31T23:59:59Z",
        "maximum_planning_budget": 4,
        "maximum_retry_budget": 0,
        "acceptance_criteria": ["validator_reexecution"],
        "expected_outputs": ["decision_json"],
        "validation_strategy": "INDEPENDENT_REEXECUTION",
        "evidence_requirements": ["hashes", "exit_codes"],
        "checkpoint_reference": head,
        "rollback_strategy": "RESTORE_PREVIOUS_HASH_AND_REEXECUTE",
        "completion_condition": "MATRIX_ATTEMPTED",
        "escalation_condition": "ANY_MANDATORY_GATE_NOT_PASS",
        "authorization_evidence_reference": "https://github.com/Plomillo/luna-linux-bridge/issues/110",
    }


def run_worker(repo: Path, pyz: Path, matrix: list[dict]) -> dict:
    run_bounded_mission, ActionSpec, probe_host_resources = load_custosz(pyz)
    head = git_head(repo)
    task = build_task(head)
    snapshot = probe_host_resources(repo)

    def runner(payload: dict) -> dict:
        failed = [row["target_id"] for row in matrix if row.get("status") != "PASS"]
        state = sha256_bytes(canonical({"head": head, "failed": failed}))
        if failed:
            return {"status": "FAIL", "result_state_hash": state, "failed_targets": failed, "certification": "NOT_GRANTED"}
        return {"status": "PASS", "result_state_hash": state, "certification": "NOT_GRANTED"}

    outcome = run_bounded_mission(
        task,
        [ActionSpec("execute_consumer_matrix", required_capabilities=("execute_consumer_matrix",), permitted_effects=("WRITE_EVIDENCE",), idempotency="IDEMPOTENT")],
        snapshot,
        available_capabilities={"execute_consumer_matrix"},
        admissible_effects={"WRITE_EVIDENCE"},
        authorization_verifier=authorize,
        action_runner=runner,
        maximum_steps=1,
        planning_budget=4,
    )
    outcome["certification"] = "NOT_GRANTED"
    outcome["worker"] = WORKER_ID
    outcome["pyz_sha256"] = CUSTOSZ_SHA256
    outcome["pyz_bytes_modified"] = False
    outcome["coordinator_shim"] = "READ_VALIDATED_SOURCE_STATE_HASH_PROPERTY"
    return outcome


def build_report(repo: Path, pyz: Path) -> dict:
    head = git_head(repo)
    matrix = run_matrix(repo)
    worker = run_worker(repo, pyz, matrix)
    identity = identity_report(repo)
    resources = measured_resources(repo)
    rollback = rollback_probe(repo / "cajita-luna-runtime")
    provenance = provenance_report(repo, head)
    decision = decide(matrix, identity, resources, rollback, provenance, worker_claim=worker.get("certification", "MISSING"))
    decision.update({
        "generated_at_utc": utc_now(),
        "producer_commit": head,
        "candidate_id": CANDIDATE_ID,
        "worker": worker,
        "matrix": matrix,
        "historical_debt": {"declared_gaps": 657, "measured_legacy_numeric_gaps": 706, "status": "DISCLOSED_NONBLOCKING_HISTORICAL_DEBT", "source_mutation": False},
    })
    return decision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--custosz", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    report = build_report(repo, Path(args.custosz).resolve())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": report["decision"],
        "global_certification": report["global_certification"],
        "worker_status": report["worker"].get("status"),
        "passed_targets": report["gates"]["coverage_21"]["passed"],
        "failed_targets": report["gates"]["coverage_21"]["failed"],
        "output": str(output),
    }, ensure_ascii=False, indent=2))
    return 0 if report["decision"] == "GRANTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
