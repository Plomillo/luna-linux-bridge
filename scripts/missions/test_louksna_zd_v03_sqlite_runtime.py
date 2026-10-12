#!/usr/bin/env python3
"""CP-03 runtime probe for the production SQLite DDL; scope is explicit.

This executes the exact CREATE TABLE/PRAGMA batch extracted from the Rust backend
against an isolated temporary database, then exercises settings/evidence/chat
CRUD and close/reopen persistence. It does NOT claim to invoke Tauri command
handlers; that remains a separate native-integration requirement.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path("scripts/missions/v03_templates/main.rs")
REPORT = Path("evidence/cp03-sqlite-runtime/report.json")
MANIFEST = Path("evidence/cp03-sqlite-runtime/manifest.json")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    source_bytes = SOURCE.read_bytes()
    source = source_bytes.decode("utf-8")
    match = re.search(r'c\\.execute_batch\\(r#"(.*?)"#\\)', source, re.S)
    if not match:
        raise SystemExit("FAIL: production SQLite execute_batch DDL not found")
    ddl = match.group(1)
    ddl_bytes = ddl.encode("utf-8")
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="louksna-cp03-") as tmp:
        db_path = Path(tmp) / "louksna-test.db"
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(ddl)
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            checks["production_schema_contains_required_tables"] = {
                "settings", "evidence", "chat_messages"
            }.issubset(tables)

            conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("preferred_repo", "Plomillo/luna-linux-bridge"),
            )
            conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("offline_mode", "true"),
            )
            conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("preferred_repo", "Plomillo/luna-linux-bridge-runtime"),
            )
            settings = dict(conn.execute(
                "SELECT key,value FROM settings WHERE key IN (?,?)",
                ("preferred_repo", "offline_mode"),
            ))
            checks["settings_insert_update_read"] = (
                settings.get("preferred_repo") == "Plomillo/luna-linux-bridge-runtime"
                and settings.get("offline_mode") == "true"
            )

            event_utc = utc_now()
            conn.execute(
                "INSERT INTO evidence(utc,operation,status,detail) VALUES(?,?,?,?)",
                (event_utc, "CP03_RUNTIME_TEST", "PASS", "isolated test; no secrets"),
            )
            evidence = conn.execute(
                "SELECT utc,operation,status,detail FROM evidence "
                "WHERE operation=? ORDER BY id DESC LIMIT 1",
                ("CP03_RUNTIME_TEST",),
            ).fetchone()
            checks["evidence_insert_read"] = evidence == (
                event_utc, "CP03_RUNTIME_TEST", "PASS", "isolated test; no secrets"
            )

            conn.execute(
                "INSERT INTO chat_messages(utc,role,content,transport) VALUES(?,?,?,?)",
                (utc_now(), "user", "CP03 isolated persistence probe", "local-test"),
            )
            chat = conn.execute(
                "SELECT role,content,transport FROM chat_messages "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            checks["chat_insert_read"] = chat == (
                "user", "CP03 isolated persistence probe", "local-test"
            )
            conn.commit()
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            checks["sqlite_integrity_check"] = integrity == "ok"
            conn.close()

            conn = sqlite3.connect(db_path)
            try:
                checks["persistence_after_close_reopen"] = (
                    conn.execute(
                        "SELECT value FROM settings WHERE key='preferred_repo'"
                    ).fetchone() == ("Plomillo/luna-linux-bridge-runtime",)
                    and conn.execute(
                        "SELECT count(*) FROM evidence WHERE operation='CP03_RUNTIME_TEST'"
                    ).fetchone() == (1,)
                    and conn.execute(
                        "SELECT count(*) FROM chat_messages "
                        "WHERE content='CP03 isolated persistence probe'"
                    ).fetchone() == (1,)
                )
                details["reopened_db_integrity"] = conn.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]
            finally:
                conn.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "louksna.zd.v03.cp03-sqlite-runtime-report.v1",
        "status": "PASS_WITH_SCOPE_LIMITS" if all(checks.values()) else "FAIL",
        "gate_disposition": "HOLD_NATIVE_TAURI_HANDLER_TEST_STILL_REQUIRED",
        "candidate_commit_sha": os.environ.get("GITHUB_SHA") or os.popen("git rev-parse HEAD").read().strip(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL_UNBOUND"),
        "timestamp_utc": utc_now(),
        "source_path": str(SOURCE),
        "source_sha256": sha256(source_bytes),
        "production_ddl_sha256": sha256(ddl_bytes),
        "runtime_scope": "EXACT_PRODUCTION_SQL_DDL_EXECUTED_IN_ISOLATED_TEMP_SQLITE_DATABASE",
        "native_tauri_command_handlers_exercised": False,
        "secret_values_used_or_emitted": False,
        "checks": checks,
        "details": details,
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema": "louksna.zd.v03.cp03-sqlite-runtime-manifest.v1",
        "candidate_commit_sha": report["candidate_commit_sha"],
        "workflow_run_id": report["workflow_run_id"],
        "report_path": str(REPORT),
        "report_bytes": REPORT.stat().st_size,
        "report_sha256": sha256(REPORT.read_bytes()),
        "source_path": str(SOURCE),
        "source_sha256": report["source_sha256"],
        "production_ddl_sha256": report["production_ddl_sha256"],
        "sealed_at_utc": utc_now(),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "gate_disposition": report["gate_disposition"],
        "candidate_commit_sha": report["candidate_commit_sha"],
        "workflow_run_id": report["workflow_run_id"],
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "native_tauri_command_handlers_exercised": False,
        "report": str(REPORT),
        "manifest": str(MANIFEST),
    }, sort_keys=True))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
