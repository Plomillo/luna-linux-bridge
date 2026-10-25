#!/usr/bin/env python3
"""Source-bound, read-only/runtime-engine smoke adapters for selected Cajita targets.

These checks exercise six real target engines or target-specific interfaces. They
are not complete consumer-task coverage, semantic-quality proof, or certification.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote

SCHEMA = "CAJITA_TARGET_ENGINE_TASK/1.0"
RESULT_SCHEMA = "CAJITA_TARGET_ENGINE_TASK_RESULT/1.0"
TARGET_ADAPTERS = {
    "D02_ORQUESTADOR": {
        "domain_id": "D02_ORQUESTACION",
        "adapter_id": "CAJITA_CLI_REGISTRY_SELFTEST/1.0",
        "operation": "audit_cli_registry",
        "module": "2. Orquestación/Orquestador",
        "entry": "CLIs/cli_registry.py",
        "required_files": [
            "CLIs/cli_registry.py",
            "CLIs/cli_contract.json",
            "CLIs/common.py",
            "punto.json"
        ],
        "engine": "PYTHON_CLI_REGISTRY",
        "scope": "READ_ONLY_EIGHT_CLI_MANIFEST_AND_MODULE_SELFTEST"
    },
    "D02_CONFESION_ECLESIAL_REFORMADA": {
        "domain_id": "D02_ORQUESTACION",
        "adapter_id": "CAJITA_BIBLE_DATABASE_INTEGRITY/1.0",
        "operation": "audit_readonly_bible_database",
        "module": "2. Orquestación/Confesión Eclesial Reformada",
        "entry": "Biblia Textual BTX -- Biblia Textual BTX -- ( WeLib.org ).sqlite3",
        "required_files": [
            "Biblia Textual BTX -- Biblia Textual BTX -- ( WeLib.org ).sqlite3"
        ],
        "engine": "SQLITE_READ_ONLY",
        "scope": "READ_ONLY_DATABASE_INTEGRITY_AND_SCHEMA_PRESENCE"
    },
    "D02_MULTI_INTERDISCIPLINAR": {
        "domain_id": "D02_ORQUESTACION",
        "adapter_id": "CAJITA_AXIOM_SOURCE_PREFIX_BINDING/1.0",
        "operation": "verify_axiom_source_binding",
        "module": "2. Orquestación/Multi + Interdisciplinar",
        "entry": "cajita_axiom_source_loader.py",
        "required_files": [
            "cajita_axiom_source_loader.py",
            "axiom_interdisciplinary_binding.json",
            "APACHE_JENA_6_2_0.7z"
        ],
        "engine": "SOURCE_BOUND_AXIOM_READER",
        "scope": "PROTECTED_SOURCE_PREFIX_AND_COMPANION_HASH_VERIFICATION"
    },
    "D06_CONSOLA": {
        "domain_id": "D06_SISTEMA_INTELIGENTE",
        "adapter_id": "CAJITA_QUICKJS_KNOWN_ANSWER/1.0",
        "operation": "evaluate_fixed_javascript_fixture",
        "module": "6. Sistema Inteligente/Consola",
        "entry": "quickjs-linux-x86_64-2026-06-04/qjs",
        "required_files": [
            "quickjs-linux-x86_64-2026-06-04/qjs"
        ],
        "engine": "QUICKJS",
        "scope": "FIXED_EXPRESSION_KNOWN_ANSWER_NO_USER_CODE"
    },
    "D06_MEMORIA_GOBERNADA": {
        "domain_id": "D06_SISTEMA_INTELIGENTE",
        "adapter_id": "CAJITA_SQLITE_MEMORY_ROUNDTRIP/1.0",
        "operation": "verify_sqlite_memory_roundtrip",
        "module": "6. Sistema Inteligente/Memoria Gobernada",
        "entry": "sqlite-amalgamation-3530400/sqlite-amalgamation-3530400/sqlite3.c",
        "required_files": [
            "sqlite-amalgamation-3530400/sqlite-amalgamation-3530400/sqlite3.c",
            "sqlite-amalgamation-3530400/sqlite-amalgamation-3530400/shell.c",
            "sqlite-amalgamation-3530400/sqlite-amalgamation-3530400/sqlite3.h"
        ],
        "engine": "SQLITE_AMALGAMATION",
        "scope": "TEMPORARY_DATABASE_CRUD_AND_PROVENANCE_ROUNDTRIP"
    },
    "D06_MOTOR_PROTOCOLAR": {
        "domain_id": "D06_SISTEMA_INTELIGENTE",
        "adapter_id": "CAJITA_BOOST_SML_STATE_TRANSITIONS/1.0",
        "operation": "verify_fixed_protocol_state_machine",
        "module": "6. Sistema Inteligente/Motor - Protocolar",
        "entry": "sml-1.2.0/sml-1.2.0/include/boost/sml.hpp",
        "required_files": [
            "sml-1.2.0/sml-1.2.0/include/boost/sml.hpp"
        ],
        "engine": "BOOST_SML",
        "scope": "COMPILED_FIXED_STATE_TRANSITIONS_ONLY"
    }
}
EXPECTED_TARGET_IDS = tuple(TARGET_ADAPTERS)


class TargetAdapterError(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise TargetAdapterError("TARGET_ADAPTER_PATH_MISSING")
    p = PurePosixPath(value.replace("\\", "/"))
    if p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
        raise TargetAdapterError("TARGET_ADAPTER_PATH_UNSAFE:" + value[:160])
    if len(p.parts) and ":" in p.parts[0]:
        raise TargetAdapterError("TARGET_ADAPTER_PATH_UNSAFE:" + value[:160])
    return p


def _regular_file(root: Path, rel: str) -> Path:
    relative = _safe_relative(rel)
    path = root.joinpath(*relative.parts)
    if path.is_symlink() or not path.is_file():
        raise TargetAdapterError("TARGET_ADAPTER_REQUIRED_FILE_MISSING_OR_UNSAFE:" + rel)
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise TargetAdapterError("TARGET_ADAPTER_FILE_PATH_ESCAPE:" + rel)
    return resolved


def _module_root(runtime: Path, spec: dict) -> Path:
    rel = _safe_relative(spec["module"])
    module = runtime.joinpath(*rel.parts)
    if module.is_symlink() or not module.is_dir() or not module.resolve().is_relative_to(runtime.resolve()):
        raise TargetAdapterError("TARGET_ADAPTER_MODULE_ROOT_MISSING_OR_UNSAFE:" + spec["module"])
    descriptor_path = module / "CAJITA_MODULE.json"
    if descriptor_path.is_symlink() or not descriptor_path.is_file():
        raise TargetAdapterError("TARGET_ADAPTER_MODULE_DESCRIPTOR_MISSING:" + spec["module"])
    try:
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TargetAdapterError("TARGET_ADAPTER_MODULE_DESCRIPTOR_INVALID:" + spec["module"]) from exc
    if descriptor.get("schema") != "CAJITA_CANONICAL_TARGET_MODULE/1.0":
        raise TargetAdapterError("TARGET_ADAPTER_MODULE_DESCRIPTOR_SCHEMA_MISMATCH:" + spec["module"])
    if descriptor.get("target_id") != next((target_id for target_id, row in TARGET_ADAPTERS.items() if row is spec), None):
        raise TargetAdapterError("TARGET_ADAPTER_MODULE_TARGET_ID_MISMATCH:" + spec["module"])
    if descriptor.get("relative_path") != spec["module"]:
        raise TargetAdapterError("TARGET_ADAPTER_MODULE_PATH_BINDING_MISMATCH:" + spec["module"])
    return module


def _verify_required_files(runtime: Path, module: Path, spec: dict) -> list[dict]:
    rows = []
    for rel in spec["required_files"]:
        path = _regular_file(module, rel)
        data = path.read_bytes()
        rows.append({
            "path": (Path(spec["module"]) / rel).as_posix(),
            "bytes": len(data),
            "sha256": _sha(data)
        })
    descriptor = json.loads((module / "CAJITA_MODULE.json").read_text(encoding="utf-8"))
    target_id = next((target_id for target_id, row in TARGET_ADAPTERS.items() if row is spec), None)
    registration = descriptor.get("runtime_engine_scope_registration")
    if not isinstance(registration, dict) or registration.get("status") != "REGISTERED_RUNTIME_SMOKE_SCOPE_ONLY":
        raise TargetAdapterError("TARGET_ADAPTER_RUNTIME_SCOPE_NOT_REGISTERED:" + str(target_id))
    if registration.get("target_id") != target_id or registration.get("adapter_id") != spec["adapter_id"] or registration.get("operation") != spec["operation"]:
        raise TargetAdapterError("TARGET_ADAPTER_RUNTIME_SCOPE_IDENTITY_MISMATCH:" + str(target_id))
    if registration.get("source_files") != rows:
        raise TargetAdapterError("TARGET_ADAPTER_SOURCE_FILE_IDENTITY_MISMATCH:" + str(target_id))
    adapter_source = _regular_file(runtime, "cajita_target_adapters.py").read_bytes()
    if registration.get("adapter_source_sha256") != _sha(adapter_source):
        raise TargetAdapterError("TARGET_ADAPTER_SOURCE_CODE_HASH_MISMATCH:" + str(target_id))
    if registration.get("certification") != "NOT_GRANTED" or registration.get("reference_quality_equivalence") != "NOT_ESTABLISHED":
        raise TargetAdapterError("TARGET_ADAPTER_SCOPE_OVERCLAIMS_CERTIFICATION:" + str(target_id))
    return rows


def _run_cli_registry_selftest(runtime: Path, module: Path, spec: dict, companion: Path | None) -> dict:
    cli_dir = module / "CLIs"
    entry = _regular_file(module, "CLIs/cli_registry.py")
    sys.path.insert(0, str(cli_dir))
    try:
        name = "_cajita_cli_registry_runtime_smoke"
        spec_obj = importlib.util.spec_from_file_location(name, entry)
        if spec_obj is None or spec_obj.loader is None:
            raise TargetAdapterError("CLI_REGISTRY_IMPORT_SPEC_UNAVAILABLE")
        imported = importlib.util.module_from_spec(spec_obj)
        spec_obj.loader.exec_module(imported)
        result = imported.selftest(module / "punto.json", cli_dir / "cli_contract.json")
    finally:
        try:
            sys.path.remove(str(cli_dir))
        except ValueError:
            pass
    if result.get("status") != "PASS" or result.get("domain_count") != 8 or result.get("all_adapters_present") is not True:
        raise TargetAdapterError("CLI_REGISTRY_SELFTEST_NOT_PASS:" + json.dumps(result, sort_keys=True)[:600])
    if result.get("side_effects") is not False:
        raise TargetAdapterError("CLI_REGISTRY_SELFTEST_SIDE_EFFECTS_NOT_FALSE")
    return {
        "status": "PASS",
        "domain_count": result["domain_count"],
        "all_adapters_present": result["all_adapters_present"],
        "side_effects": False,
        "legacy_spec_absent_after_migration": result.get("legacy_spec_absent_after_migration")
    }


def _run_bible_db_readonly(runtime: Path, module: Path, spec: dict, companion: Path | None) -> dict:
    db = _regular_file(module, spec["entry"])
    uri = "file:" + quote(str(db), safe="/") + "?mode=ro&immutable=1"
    try:
        with sqlite3.connect(uri, uri=True, timeout=5) as conn:
            check = [str(row[0]) for row in conn.execute("PRAGMA quick_check").fetchall()]
            tables = [str(row[0]) for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()]
    except sqlite3.Error as exc:
        raise TargetAdapterError("BIBLE_DATABASE_READONLY_AUDIT_FAILED:" + type(exc).__name__) from exc
    if check != ["ok"] or not tables:
        raise TargetAdapterError("BIBLE_DATABASE_INTEGRITY_OR_SCHEMA_GATE_FAILED")
    return {
        "status": "PASS",
        "database_sha256": _sha(db.read_bytes()),
        "quick_check": check,
        "user_table_count": len(tables),
        "table_names_sha256": _sha(json.dumps(tables, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
        "write_access": False
    }


def _run_axiom_binding(runtime: Path, module: Path, spec: dict, companion: Path | None) -> dict:
    if companion is None or companion.is_symlink() or not companion.is_file():
        raise TargetAdapterError("LOUKSNA1_COMPANION_REQUIRED_FOR_AXIOM_BINDING")
    entry = _regular_file(module, "cajita_axiom_source_loader.py")
    name = "_cajita_axiom_source_loader_runtime_smoke"
    spec_obj = importlib.util.spec_from_file_location(name, entry)
    if spec_obj is None or spec_obj.loader is None:
        raise TargetAdapterError("AXIOM_SOURCE_LOADER_IMPORT_SPEC_UNAVAILABLE")
    imported = importlib.util.module_from_spec(spec_obj)
    spec_obj.loader.exec_module(imported)
    result = imported.verify_binding(runtime, companion)
    if result.get("status") != "PASS_SOURCE_PREFIX_VERIFIED":
        raise TargetAdapterError("AXIOM_SOURCE_BINDING_NOT_PASS")
    if result.get("semantic_graph_execution") != "NOT_PERFORMED_BY_SOURCE_LOADER":
        raise TargetAdapterError("AXIOM_SOURCE_LOADER_SCOPE_DRIFT")
    if result.get("certification") != "NOT_GRANTED":
        raise TargetAdapterError("AXIOM_SOURCE_LOADER_CERTIFICATION_SCOPE_DRIFT")
    if result.get("target", {}).get("id") != "D02_MULTI_INTERDISCIPLINAR":
        raise TargetAdapterError("AXIOM_SOURCE_BINDING_TARGET_MISMATCH")
    return {
        "status": "PASS",
        "companion_sha256": result["companion_sha256"],
        "protected_prefix_sha256": result["protected_prefix_sha256"],
        "protected_prefix_bytes": result["protected_prefix_bytes"],
        "axiom_inventory": result["axiom_inventory"],
        "block_inventory": result["block_inventory"],
        "framework_count": result["framework_count"],
        "graph_execution": "SEPARATELY_GATED_BY_G23",
        "certification": "NOT_GRANTED"
    }


def _run_quickjs(runtime: Path, module: Path, spec: dict, companion: Path | None) -> dict:
    qjs = _regular_file(module, spec["entry"])
    code = 'print(JSON.stringify({answer:2+2,strict:true}))'
    try:
        proc = subprocess.run(
            [str(qjs), "--std", "-e", code],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=5, check=False, shell=False,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "", "LANG": "C.UTF-8"}
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TargetAdapterError("QUICKJS_EXECUTION_FAILED:" + type(exc).__name__) from exc
    if proc.returncode != 0:
        raise TargetAdapterError("QUICKJS_NONZERO_EXIT:" + proc.stderr[-250:])
    try:
        result = json.loads(proc.stdout.strip())
    except json.JSONDecodeError as exc:
        raise TargetAdapterError("QUICKJS_OUTPUT_NOT_JSON") from exc
    if result != {"answer": 4, "strict": True}:
        raise TargetAdapterError("QUICKJS_KNOWN_ANSWER_MISMATCH")
    return {"status": "PASS", "known_answer": result, "shell": False, "user_code_executed": False}


def _run_sqlite_roundtrip(runtime: Path, module: Path, spec: dict, companion: Path | None) -> dict:
    source_root = module / "sqlite-amalgamation-3530400" / "sqlite-amalgamation-3530400"
    shell = _regular_file(module, "sqlite-amalgamation-3530400/sqlite-amalgamation-3530400/shell.c")
    amalgamation = _regular_file(module, "sqlite-amalgamation-3530400/sqlite-amalgamation-3530400/sqlite3.c")
    _regular_file(module, "sqlite-amalgamation-3530400/sqlite-amalgamation-3530400/sqlite3.h")
    if source_root.is_symlink() or not source_root.is_dir():
        raise TargetAdapterError("SQLITE_AMALGAMATION_ROOT_INVALID")
    with tempfile.TemporaryDirectory(prefix="cajita-sqlite-smoke-") as temp_name:
        temp = Path(temp_name)
        binary = temp / "sqlite3"
        build = subprocess.run(
            ["cc", "-O2", "-DSQLITE_THREADSAFE=1", str(shell), str(amalgamation),
             "-ldl", "-lpthread", "-lm", "-o", str(binary)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=120, check=False, shell=False
        )
        if build.returncode != 0 or not binary.is_file():
            raise TargetAdapterError("SQLITE_AMALGAMATION_COMPILE_FAILED:" + build.stderr[-500:])
        db = temp / "governed-memory.sqlite3"
        provenance = _sha(b"CAJITA_D06_MEMORIA_GOBERNADA_ROUNDTRIP_FIXTURE_V1")
        sql = (
            "CREATE TABLE memory_records(key TEXT PRIMARY KEY,value TEXT NOT NULL,provenance_sha256 TEXT NOT NULL);"
            "BEGIN IMMEDIATE;"
            "INSERT INTO memory_records VALUES('smoke-key','smoke-value','" + provenance + "');"
            "COMMIT;"
            "SELECT key||'|'||value||'|'||provenance_sha256 FROM memory_records WHERE key='smoke-key';"
            "PRAGMA integrity_check;"
        )
        proc = subprocess.run(
            [str(binary), "-batch", "-bail", "-noheader", str(db)],
            input=sql, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=10, check=False, shell=False
        )
        if proc.returncode != 0:
            raise TargetAdapterError("SQLITE_MEMORY_ROUNDTRIP_FAILED:" + proc.stderr[-400:])
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        expected = "smoke-key|smoke-value|" + provenance
        if lines != [expected, "ok"]:
            raise TargetAdapterError("SQLITE_MEMORY_KNOWN_ANSWER_MISMATCH")
        if not db.is_file() or db.is_symlink():
            raise TargetAdapterError("SQLITE_MEMORY_DATABASE_NOT_MATERIALIZED")
        return {
            "status": "PASS",
            "database_sha256": _sha(db.read_bytes()),
            "known_answer": "smoke-key|smoke-value|PROVENANCE_SHA256",
            "integrity_check": "ok",
            "durability_scope": "TEMPORARY_DATABASE_ONLY",
            "persistent_user_memory": "NOT_ESTABLISHED"
        }


def _run_sml_protocol(runtime: Path, module: Path, spec: dict, companion: Path | None) -> dict:
    header = _regular_file(module, spec["entry"])
    include = header.parents[1]  # .../include/boost/sml.hpp -> .../include
    with tempfile.TemporaryDirectory(prefix="cajita-sml-smoke-") as temp_name:
        temp = Path(temp_name)
        source = temp / "protocol_smoke.cpp"
        binary = temp / "protocol_smoke"
        source.write_text(r'''#include <boost/sml.hpp>
#include <iostream>
struct idle_state {};
struct active_state {};
struct done_state {};
struct start_event {};
struct stop_event {};
struct protocol {
  auto operator()() const {
    using namespace boost::sml;
    return make_transition_table(
      *state<idle_state> + event<start_event> = state<active_state>,
       state<active_state> + event<stop_event> = state<done_state>
    );
  }
};
int main() {
  boost::sml::sm<protocol> sm;
  if (!sm.is(boost::sml::state<idle_state>)) return 11;
  sm.process_event(start_event{});
  if (!sm.is(boost::sml::state<active_state>)) return 12;
  sm.process_event(stop_event{});
  if (!sm.is(boost::sml::state<done_state>)) return 13;
  std::cout << "idle>active>done\n";
  return 0;
}
''', encoding="utf-8")
        build = subprocess.run(
            ["g++", "-std=c++17", "-O2", "-I", str(include), str(source), "-o", str(binary)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=90, check=False, shell=False
        )
        if build.returncode != 0 or not binary.is_file():
            raise TargetAdapterError("SML_PROTOCOL_COMPILE_FAILED:" + build.stderr[-500:])
        proc = subprocess.run(
            [str(binary)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=5, check=False, shell=False
        )
        if proc.returncode != 0 or proc.stdout.strip() != "idle>active>done":
            raise TargetAdapterError("SML_PROTOCOL_TRANSITION_KNOWN_ANSWER_MISMATCH")
        return {"status": "PASS", "known_answer": proc.stdout.strip(), "compiled_from_registered_header": True}


def execute_target_task(runtime_root: str | Path, target_id: str, companion_path: str | Path | None = None) -> dict:
    runtime = Path(runtime_root).resolve(strict=True)
    if not runtime.is_dir():
        raise TargetAdapterError("TARGET_ADAPTER_RUNTIME_ROOT_INVALID")
    spec = TARGET_ADAPTERS.get(target_id)
    if not isinstance(spec, dict):
        raise TargetAdapterError("TARGET_ADAPTER_NOT_REGISTERED:" + str(target_id))
    module = _module_root(runtime, spec)
    required_files = _verify_required_files(runtime, module, spec)
    runners = {
        "audit_cli_registry": _run_cli_registry_selftest,
        "audit_readonly_bible_database": _run_bible_db_readonly,
        "verify_axiom_source_binding": _run_axiom_binding,
        "evaluate_fixed_javascript_fixture": _run_quickjs,
        "verify_sqlite_memory_roundtrip": _run_sqlite_roundtrip,
        "verify_fixed_protocol_state_machine": _run_sml_protocol,
    }
    handler = runners.get(spec["operation"])
    if handler is None:
        raise TargetAdapterError("TARGET_ADAPTER_OPERATION_NOT_IMPLEMENTED:" + spec["operation"])
    companion = Path(companion_path).resolve() if companion_path else None
    result = handler(runtime, module, spec, companion)
    if result.get("status") != "PASS":
        raise TargetAdapterError("TARGET_ADAPTER_HANDLER_NOT_PASS:" + target_id)
    return {
        "schema": RESULT_SCHEMA,
        "target_id": target_id,
        "domain_id": spec["domain_id"],
        "adapter_id": spec["adapter_id"],
        "operation": spec["operation"],
        "status": "PASS_TARGET_ENGINE_EXECUTION",
        "exit_code": 0,
        "engine": spec["engine"],
        "required_file_identities": required_files,
        "result": result,
        "execution_scope": spec["scope"],
        "task_coverage": "PARTIAL_TARGET_ENGINE_SMOKE_ONLY",
        "consumer_task_adapter_completion": "NOT_ESTABLISHED",
        "reference_quality_equivalence": "NOT_ESTABLISHED",
        "native_hardware_validation": "REQUIRED",
        "certification": "NOT_GRANTED"
    }


def run_target_smokes(runtime_root: str | Path, companion_path: str | Path | None = None) -> dict:
    rows = []
    for target_id in EXPECTED_TARGET_IDS:
        try:
            rows.append(execute_target_task(runtime_root, target_id, companion_path))
        except Exception as exc:
            spec = TARGET_ADAPTERS[target_id]
            rows.append({
                "schema": RESULT_SCHEMA,
                "target_id": target_id,
                "domain_id": spec["domain_id"],
                "adapter_id": spec["adapter_id"],
                "operation": spec["operation"],
                "status": "FAIL_TARGET_ENGINE_EXECUTION",
                "exit_code": 2,
                "error_type": type(exc).__name__,
                "reason": str(exc)[:700],
                "execution_scope": spec["scope"],
                "consumer_task_adapter_completion": "NOT_ESTABLISHED",
                "reference_quality_equivalence": "NOT_ESTABLISHED",
                "native_hardware_validation": "REQUIRED",
                "certification": "NOT_GRANTED"
            })
    passed = sum(1 for row in rows if row.get("status") == "PASS_TARGET_ENGINE_EXECUTION" and row.get("exit_code") == 0)
    return {
        "schema": "CAJITA_RUNTIME_TARGET_ENGINE_E2E/1.0",
        "status": "PASS_TARGET_ENGINE_E2E_SCOPE_ONLY" if passed == len(EXPECTED_TARGET_IDS) else "FAIL_TARGET_ENGINE_E2E_SCOPE",
        "expected_count": len(EXPECTED_TARGET_IDS),
        "pass_count": passed,
        "failed_count": len(EXPECTED_TARGET_IDS) - passed,
        "results": rows,
        "scope": "SIX_SOURCE_BOUND_TARGET_ENGINE_SMOKES; NO_FULL_TASK_OR_QUALITY_CLAIM",
        "unregistered_target_task_adapters": "NOT_ESTABLISHED",
        "reference_quality_equivalence": "NOT_ESTABLISHED",
        "native_hardware_validation": "REQUIRED",
        "certification": "NOT_GRANTED"
    }


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--companion", default=os.environ.get("LOUKSNA1_COMPANION_PATH"))
    parser.add_argument("--target-id", choices=EXPECTED_TARGET_IDS)
    args = parser.parse_args(argv)
    try:
        if args.target_id:
            result = execute_target_task(args.root, args.target_id, args.companion)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        result = run_target_smokes(args.root, args.companion)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "PASS_TARGET_ENGINE_E2E_SCOPE_ONLY" else 2
    except Exception as exc:
        print(json.dumps({
            "schema": RESULT_SCHEMA,
            "status": "FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "reason": str(exc)[:700],
            "certification": "NOT_GRANTED"
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
