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
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen
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
        "D05_DOCLING": ("extract_document_image", "REFERENCE_EXTRACTION_EQUIVALENCE_NOT_EXECUTED"),
        "D06_ANALISIS_AVANZADO": ("analyze_reasoning", "REFERENCE_REASONING_EQUIVALENCE_NOT_EXECUTED"),
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
        elif target_id == "D06_ANTI_ALUCINACIONES":
            rows.append(op_onnx(runtime))
        elif target_id == "D05_CALIBRE":
            rows.append(op_calibre(runtime))
        elif target_id == "D06_PORTABILIDAD_BASE":
            rows.append(op_cmake(runtime))
        elif target_id == "D06_RUNTIME_ANDROID_WINDOWS":
            rows.append(op_avalonia(runtime))
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


ONNX_OID = "c6a266fe0f7f1f782094ff4b1e7ae3547fa48a22ab44712881cc03bba07bc5b7"
ONNX_BYTES = 110516001
NUMPY_SHA256 = "ba10f8411898fc418a521833e014a77d3ca01c15b0c6cdcce6a0d2897e6dbbdf"
GROUNDING_TEXT = "En un principio creó Elohim los cielos y la tierra."
GROUNDING_ARGMAX = [0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
CALIBRE_URL = "https://github.com/kovidgoyal/calibre/releases/download/v9.17.0/calibre-9.17.0-x86_64.txz"
CALIBRE_SHA256 = "953e4512a6482848cd803c88b6d942e6afca65dc3b67c7d1353ae048d616de53"
CALIBRE_BYTES = 201590724
CALIBRE_VERSION = "9.17.0"
CALIBRE_FIXTURE = "Louksna1 calibre conversion fixture LOUKSNA1_CALIBRE_FIXTURE_V1.\n"
CMAKE_ARCHIVE_SHA256 = "fc8a06079563f1befb35204eee593a1c87ce405ffc8a8483cf769ae9feedbf37"
CMAKE_ARCHIVE_BYTES = 21310484
CMAKE_EXE_MEMBER = "cmake-4.4.3-windows-x86_64/bin/cmake.exe"
CMAKE_VERSION_LINE = "cmake version 4.4.3"
CMAKE_ECHO = "LOUKSNA1_CMAKE_FIXTURE_V1"
AVALONIA_ARCHIVE_SHA256 = "46ea1b444978950605f3cea2edaf2e7a9116e14ebd0db42f49f7582eff7ae66f"
AVALONIA_ARCHIVE_BYTES = 3836434
AVALONIA_DLL_MEMBER = "lib/net8.0/Avalonia.Base.dll"
AVALONIA_DLL_SHA256 = "e9d36101c0cbf2756c0cb7a3794bfdf3c747cb41730ae2be4bb4b40604a11649"
AVALONIA_ASSEMBLY = "Avalonia.Base"
AVALONIA_VERSION = "12.1.1.0"


def materialize_onnx(pointer: Path, dest: Path) -> str:
    raw = pointer.read_bytes()
    if not raw.startswith(b"version https://git-lfs.github.com/spec/v1"):
        dest.write_bytes(raw)
    else:
        fields = {}
        for line in raw.decode("utf-8").splitlines():
            if line.startswith("oid sha256:"):
                fields["oid"] = line.split(":", 1)[1].strip()
            elif line.startswith("size "):
                fields["size"] = int(line.split()[1])
        if fields.get("oid") != ONNX_OID or fields.get("size") != ONNX_BYTES:
            return "ONNX_LFS_POINTER_MISMATCH"
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        if not token:
            probe = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=15, check=False)
            token = probe.stdout.strip() if probe.returncode == 0 else ""
        if not token:
            return "ONNX_LFS_TOKEN_MISSING"
        body = json.dumps({"operation": "download", "transfers": ["basic"], "objects": [{"oid": ONNX_OID, "size": ONNX_BYTES}]}).encode()
        request = Request(
            "https://github.com/Plomillo/luna-linux-bridge.git/info/lfs/objects/batch",
            data=body,
            headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.git-lfs+json", "Content-Type": "application/vnd.git-lfs+json"},
            method="POST",
        )
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode())
        href = payload["objects"][0]["actions"]["download"]["href"]
        with urlopen(href, timeout=180) as response, dest.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    if dest.stat().st_size != ONNX_BYTES or sha256_file(dest) != ONNX_OID:
        return "ONNX_HASH_MISMATCH"
    return ""


def op_onnx(runtime: Path) -> dict:
    target = "D06_ANTI_ALUCINACIONES"
    domain = runtime / "6. Sistema Inteligente" / "Anti-Alucinaciones"
    pointer = domain / "model.onnx"
    tokenizer = domain / "tokenizer.json"
    tokenizers_wheel = domain / "tokenizers-0.23.1-cp310-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
    runtime_wheel = runtime.parent / "externalized-assets-staging" / "6-Sistema-Inteligente" / "Anti-Alucinaciones" / "onnxruntime-1.29.0-cp311-cp311-manylinux_2_28_x86_64.whl"
    interpreter = shutil.which("python3.11")
    if pointer.is_symlink() or not pointer.is_file() or tokenizer.is_symlink() or not tokenizer.is_file():
        return record(target, "score_grounding", "FAIL", exit_code=2, detail={}, reason="ONNX_MODEL_OR_TOKENIZER_MISSING")
    if tokenizers_wheel.is_symlink() or not tokenizers_wheel.is_file() or runtime_wheel.is_symlink() or not runtime_wheel.is_file():
        return record(target, "score_grounding", "FAIL", exit_code=2, detail={}, reason="ONNX_PINNED_WHEEL_MISSING")
    if not interpreter:
        return record(target, "score_grounding", "FAIL", exit_code=2, detail={}, reason="ONNX_CP311_INTERPRETER_MISSING")
    with tempfile.TemporaryDirectory(prefix="louksna1-onnx-") as temp_name:
        temp = Path(temp_name)
        model = temp / "model.onnx"
        problem = materialize_onnx(pointer, model)
        if problem:
            return record(target, "score_grounding", "FAIL", exit_code=4, detail={}, reason=problem)
        wheels = temp / "wheels"
        wheels.mkdir()
        download = subprocess.run(
            [sys.executable, "-m", "pip", "download", "--disable-pip-version-check", "--no-cache-dir", "--only-binary=:all:",
             "--python-version", "311", "--implementation", "cp", "--abi", "cp311", "--platform", "manylinux_2_17_x86_64",
             "-d", str(wheels), "numpy==2.2.6"],
            capture_output=True, text=True, timeout=180, check=False,
        )
        numpy_wheel = next(wheels.glob("numpy-*.whl"), None)
        if download.returncode != 0 or numpy_wheel is None or sha256_file(numpy_wheel) != NUMPY_SHA256:
            return record(target, "score_grounding", "FAIL", exit_code=4, detail={"return_code": download.returncode, "stderr_tail": download.stderr[-240:]}, reason="NUMPY_WHEEL_HASH_MISMATCH")
        deps = temp / "deps"
        deps.mkdir()
        for bundle in (runtime_wheel, tokenizers_wheel, numpy_wheel):
            with zipfile.ZipFile(bundle) as archive:
                archive.extractall(deps)
        script = temp / "score_grounding.py"
        script.write_text(
            "import json, sys\nimport numpy as np\nimport onnxruntime as ort\nfrom tokenizers import Tokenizer\n"
            "text, model, tokenizer = sys.argv[1:]\n"
            "enc = Tokenizer.from_file(tokenizer).encode(text)\n"
            "ids = np.array([enc.ids], dtype=np.int64)\nmask = np.array([enc.attention_mask], dtype=np.int64)\n"
            "session = ort.InferenceSession(model, providers=['CPUExecutionProvider'])\n"
            "logits = session.run(None, {'input_ids': ids, 'attention_mask': mask})[0]\n"
            "if logits.shape != (1, len(enc.ids), 2) or not np.isfinite(logits).all():\n    raise SystemExit(3)\n"
            "print(json.dumps({'argmax': logits.argmax(axis=-1)[0].astype(int).tolist(), 'ort': ort.__version__}))\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(deps)
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run([interpreter, str(script), GROUNDING_TEXT, str(model), str(tokenizer)], env=env, capture_output=True, text=True, timeout=120, check=False)
    argmax = None
    ort_version = None
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout.strip().splitlines()[-1])
            argmax = parsed.get("argmax")
            ort_version = parsed.get("ort")
        except json.JSONDecodeError:
            argmax = None
    ok = proc.returncode == 0 and argmax == GROUNDING_ARGMAX and ort_version == "1.29.0"
    return record(
        target,
        "score_grounding",
        "PASS" if ok else "FAIL",
        exit_code=0 if ok else 4,
        detail={
            "return_code": proc.returncode,
            "argmax": argmax,
            "expected_argmax": GROUNDING_ARGMAX,
            "ort": ort_version,
            "fixture_sha256": sha256_bytes(GROUNDING_TEXT.encode()),
            "model_sha256": ONNX_OID,
            "stderr_tail": proc.stderr[-240:],
        },
        reason="" if ok else "ONNX_GROUNDING_MISMATCH",
    )


def download_verified(url: str, dest: Path, size: int, digest: str) -> None:
    request = Request(url, headers={"User-Agent": "louksna1-integral-mission"})
    with urlopen(request, timeout=300) as response, dest.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    if dest.stat().st_size != size or sha256_file(dest) != digest:
        dest.unlink(missing_ok=True)
        raise RuntimeError("DOWNLOAD_HASH_MISMATCH")


def calibre_pin(runtime: Path) -> tuple[dict | None, str]:
    path = runtime / "5. Inteligencia documental" / "Conversión documental" / "Calibre Slim" / "source-lock.json"
    if path.is_symlink() or not path.is_file():
        return None, "CALIBRE_LOCK_MISSING"
    lock = json.loads(path.read_text(encoding="utf-8"))
    artifacts = lock.get("artifacts")
    if not isinstance(artifacts, list):
        return None, "CALIBRE_LOCK_ARTIFACT_MISSING"
    row = next((item for item in artifacts if isinstance(item, dict) and item.get("id") == "CALIBRE_V9_17_0_LINUX_X86_64_BINARY"), None)
    if row is None:
        return None, "CALIBRE_LOCK_ARTIFACT_MISSING"
    if row.get("url") != CALIBRE_URL or row.get("sha256") != CALIBRE_SHA256 or row.get("size_bytes") != CALIBRE_BYTES:
        return None, "CALIBRE_LOCK_PIN_MISMATCH"
    return row, ""


def op_calibre(runtime: Path) -> dict:
    target = "D05_CALIBRE"
    _pin, problem = calibre_pin(runtime)
    if problem:
        return record(target, "convert_document", "FAIL", exit_code=2, detail={}, reason=problem)
    slim = runtime / "5. Inteligencia documental" / "Conversión documental" / "Calibre Slim" / "calibre-slim-convert.py"
    if slim.is_symlink() or not slim.is_file():
        return record(target, "convert_document", "FAIL", exit_code=2, detail={}, reason="CALIBRE_ENTRYPOINT_MISSING")
    with tempfile.TemporaryDirectory(prefix="louksna1-calibre-") as temp_name:
        temp = Path(temp_name)
        cached = os.environ.get("LOUKSNA1_CALIBRE_TXZ", "")
        txz = Path(cached) if cached else temp / "calibre-9.17.0-x86_64.txz"
        if cached:
            if txz.is_symlink() or not txz.is_file() or txz.stat().st_size != CALIBRE_BYTES or sha256_file(txz) != CALIBRE_SHA256:
                return record(target, "convert_document", "FAIL", exit_code=4, detail={}, reason="CALIBRE_CACHE_HASH_MISMATCH")
        else:
            try:
                download_verified(CALIBRE_URL, txz, CALIBRE_BYTES, CALIBRE_SHA256)
            except (OSError, RuntimeError, TimeoutError) as exc:
                return record(target, "convert_document", "FAIL", exit_code=4, detail={"error": type(exc).__name__}, reason="CALIBRE_DOWNLOAD_FAILED")
        extract = temp / "extract"
        extract.mkdir()
        unpacked = subprocess.run(["tar", "-xJf", str(txz), "-C", str(extract)], capture_output=True, text=True, timeout=240, check=False)
        converter = extract / "ebook-convert"
        if unpacked.returncode != 0 or converter.is_symlink() or not converter.is_file():
            return record(target, "convert_document", "FAIL", exit_code=4, detail={"return_code": unpacked.returncode, "stderr_tail": (unpacked.stderr or "")[-240:]}, reason="CALIBRE_CONVERTER_MISSING")
        os.chmod(converter, 0o755)
        version = subprocess.run([str(converter), "--version"], capture_output=True, text=True, timeout=60, check=False)
        version_text = (version.stdout or "") + (version.stderr or "")
        if version.returncode != 0 or f"calibre {CALIBRE_VERSION}" not in version_text:
            return record(target, "convert_document", "FAIL", exit_code=4, detail={"return_code": version.returncode, "version_text": version_text[-240:]}, reason="CALIBRE_VERSION_MISMATCH")
        fixture = temp / "fixture.txt"
        fixture.write_text(CALIBRE_FIXTURE, encoding="utf-8")
        epub = temp / "fixture.epub"
        env = os.environ.copy()
        env["CALIBRE_EBOOK_CONVERT"] = str(converter)
        env["QT_QPA_PLATFORM"] = "offscreen"
        proc = subprocess.run([sys.executable, str(slim), str(fixture), str(epub)], env=env, capture_output=True, text=True, timeout=180, check=False)
        mimetype = b""
        found = False
        if proc.returncode == 0 and epub.is_file():
            with zipfile.ZipFile(epub) as bundle:
                mimetype = bundle.read("mimetype")
                marker = CALIBRE_FIXTURE.strip().encode("utf-8")
                for name in bundle.namelist():
                    if name.endswith((".html", ".xhtml", ".htm")) and marker in bundle.read(name):
                        found = True
                        break
    ok = proc.returncode == 0 and mimetype == b"application/epub+zip" and found
    return record(
        target,
        "convert_document",
        "PASS" if ok else "FAIL",
        exit_code=0 if ok else 4,
        detail={
            "return_code": proc.returncode,
            "calibre_version": CALIBRE_VERSION,
            "binary_sha256": CALIBRE_SHA256,
            "binary_bytes": CALIBRE_BYTES,
            "mimetype": mimetype.decode("ascii", errors="replace"),
            "fixture_found": found,
            "fixture_sha256": sha256_bytes(CALIBRE_FIXTURE.encode("utf-8")),
            "stderr_tail": (proc.stderr or "")[-240:],
        },
        reason="" if ok else "CALIBRE_CONVERSION_MISMATCH",
    )


def extract_cmake_exe(archive: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    seven = shutil.which("7zz") or shutil.which("7z")
    if not seven:
        raise RuntimeError("SEVENZIP_MISSING")
    proc = subprocess.run(
        [seven, "x", "-y", f"-o{dest}", str(archive), CMAKE_EXE_MEMBER],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "")[-400:])
    exe = dest / CMAKE_EXE_MEMBER
    if exe.is_symlink() or not exe.is_file():
        raise RuntimeError("CMAKE_EXE_NOT_IN_ARCHIVE")
    return exe


def op_cmake(runtime: Path) -> dict:
    """Re-hash the packaged exe. A witness status field is never accepted."""
    target = "D06_PORTABILIDAD_BASE"
    archive = runtime / "6. Sistema Inteligente" / "Portabilidad base" / "CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE.7z"
    if archive.is_symlink() or not archive.is_file():
        return record(target, "host_matrix", "FAIL", exit_code=2, detail={}, reason="CMAKE_ARCHIVE_MISSING")
    if archive.stat().st_size != CMAKE_ARCHIVE_BYTES or sha256_file(archive) != CMAKE_ARCHIVE_SHA256:
        return record(target, "host_matrix", "FAIL", exit_code=4, detail={"bytes": archive.stat().st_size}, reason="CMAKE_ARCHIVE_HASH_MISMATCH")
    witness_env = os.environ.get("LOUKSNA1_CMAKE_WITNESS", "")
    witness_path = Path(witness_env) if witness_env else None
    if witness_path is None or witness_path.is_symlink() or not witness_path.is_file():
        return record(target, "host_matrix", "FAIL", exit_code=2, detail={"archive_sha256": CMAKE_ARCHIVE_SHA256}, reason="WINDOWS_CMAKE_HOST_NOT_EXECUTED")
    try:
        witness = json.loads(witness_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return record(target, "host_matrix", "FAIL", exit_code=4, detail={}, reason="CMAKE_WITNESS_INVALID")
    if not isinstance(witness, dict) or witness.get("archive_sha256") != CMAKE_ARCHIVE_SHA256:
        return record(target, "host_matrix", "FAIL", exit_code=4, detail={}, reason="CMAKE_WITNESS_ARCHIVE_MISMATCH")
    try:
        with tempfile.TemporaryDirectory(prefix="louksna1-cmake-") as temp_name:
            exe = extract_cmake_exe(archive, Path(temp_name))
            exe_hash = sha256_file(exe)
    except (OSError, RuntimeError, ImportError, subprocess.TimeoutExpired) as exc:
        return record(target, "host_matrix", "FAIL", exit_code=4, detail={"error": str(exc)[:240]}, reason="CMAKE_EXE_EXTRACT_FAILED")
    reported = str(witness.get("cmake_exe_sha256", "")).lower()
    if reported != exe_hash:
        return record(target, "host_matrix", "FAIL", exit_code=4, detail={"exe_sha256": exe_hash}, reason="CMAKE_EXE_HASH_MISMATCH")
    stdout = witness.get("version_stdout") if isinstance(witness.get("version_stdout"), str) else ""
    echo = witness.get("echo_stdout") if isinstance(witness.get("echo_stdout"), str) else ""
    host = str(witness.get("platform", "")) + " " + str(witness.get("runner_os", ""))
    broken_install = "Could not find CMAKE_ROOT" in stdout or "not been installed correctly" in stdout
    ok = (
        witness.get("exit_code") == 0
        and witness.get("echo_exit_code") == 0
        and stdout.lstrip().startswith(CMAKE_VERSION_LINE)
        and not broken_install
        and echo.strip() == CMAKE_ECHO
        and "windows" in host.casefold()
    )
    return record(
        target,
        "host_matrix",
        "PASS" if ok else "FAIL",
        exit_code=0 if ok else 4,
        detail={
            "archive_sha256": CMAKE_ARCHIVE_SHA256,
            "cmake_exe_sha256": exe_hash,
            "exit_code": witness.get("exit_code"),
            "echo_exit_code": witness.get("echo_exit_code"),
            "stdout_head": stdout.strip().splitlines()[:2],
            "echo_stdout": echo.strip()[:80],
            "host": host.strip(),
            "independent_exe_hash_checked": True,
        },
        reason="" if ok else "CMAKE_WINDOWS_OUTPUT_MISMATCH",
    )


def extract_archive_member(archive: Path, dest: Path, member: str) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    seven = shutil.which("7zz") or shutil.which("7z")
    if not seven:
        raise RuntimeError("SEVENZIP_MISSING")
    proc = subprocess.run(
        [seven, "x", "-y", f"-o{dest}", str(archive), member],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "")[-400:])
    extracted = dest / member
    if extracted.is_symlink() or not extracted.is_file():
        raise RuntimeError("ARCHIVE_MEMBER_MISSING")
    return extracted


def op_avalonia(runtime: Path) -> dict:
    """Load the pinned Avalonia.Base assembly on Windows. This is not an Android device."""
    target = "D06_RUNTIME_ANDROID_WINDOWS"
    archive = runtime / "6. Sistema Inteligente" / "Runtime Android Windows" / "AVALONIA_12_1_1_NUGET.7z"
    if archive.is_symlink() or not archive.is_file():
        return record(target, "load_avalonia_base_on_windows", "FAIL", exit_code=2, detail={"android_os_executed": False}, reason="AVALONIA_ARCHIVE_MISSING")
    if archive.stat().st_size != AVALONIA_ARCHIVE_BYTES or sha256_file(archive) != AVALONIA_ARCHIVE_SHA256:
        return record(target, "load_avalonia_base_on_windows", "FAIL", exit_code=4, detail={"bytes": archive.stat().st_size, "android_os_executed": False}, reason="AVALONIA_ARCHIVE_HASH_MISMATCH")
    witness_env = os.environ.get("LOUKSNA1_AVALONIA_WITNESS", "")
    witness_path = Path(witness_env) if witness_env else None
    if witness_path is None or witness_path.is_symlink() or not witness_path.is_file():
        return record(target, "load_avalonia_base_on_windows", "FAIL", exit_code=2, detail={"archive_sha256": AVALONIA_ARCHIVE_SHA256, "android_os_executed": False}, reason="WINDOWS_AVALONIA_HOST_NOT_EXECUTED")
    try:
        witness = json.loads(witness_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return record(target, "load_avalonia_base_on_windows", "FAIL", exit_code=4, detail={"android_os_executed": False}, reason="AVALONIA_WITNESS_INVALID")
    if not isinstance(witness, dict) or witness.get("archive_sha256") != AVALONIA_ARCHIVE_SHA256:
        return record(target, "load_avalonia_base_on_windows", "FAIL", exit_code=4, detail={"android_os_executed": False}, reason="AVALONIA_WITNESS_ARCHIVE_MISMATCH")
    try:
        with tempfile.TemporaryDirectory(prefix="louksna1-avalonia-") as temp_name:
            dll = extract_archive_member(archive, Path(temp_name), AVALONIA_DLL_MEMBER)
            dll_hash = sha256_file(dll)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return record(target, "load_avalonia_base_on_windows", "FAIL", exit_code=4, detail={"error": str(exc)[:240], "android_os_executed": False}, reason="AVALONIA_DLL_EXTRACT_FAILED")
    reported = str(witness.get("dll_sha256", "")).lower()
    host = str(witness.get("platform", "")) + " " + str(witness.get("runner_os", ""))
    ok = (
        reported == dll_hash == AVALONIA_DLL_SHA256
        and witness.get("assembly_name") == AVALONIA_ASSEMBLY
        and witness.get("assembly_version") == AVALONIA_VERSION
        and "windows" in host.casefold()
    )
    return record(
        target,
        "load_avalonia_base_on_windows",
        "PASS" if ok else "FAIL",
        exit_code=0 if ok else 4,
        detail={
            "archive_sha256": AVALONIA_ARCHIVE_SHA256,
            "dll_sha256": dll_hash,
            "assembly_name": witness.get("assembly_name"),
            "assembly_version": witness.get("assembly_version"),
            "host": host.strip(),
            "android_os_executed": False,
            "independent_dll_hash_checked": True,
        },
        reason="" if ok else "AVALONIA_WINDOWS_ASSEMBLY_MISMATCH",
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
