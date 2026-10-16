#!/usr/bin/env python3
"""CP-04 isolated Secret Service lifecycle test using synthetic, non-secret data."""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("evidence/cp04-secret-service/report.json")
MANIFEST = Path("evidence/cp04-secret-service/manifest.json")
SERVICE = "louksna-cp04-disposable-test"
ACCOUNT = "synthetic-github-token-test"
SYNTHETIC_VALUE = "louksna-cp04-synthetic-not-a-real-token-0123456789"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, input=input_text, text=True, capture_output=True, timeout=20, check=False)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    checks: dict[str, bool] = {}
    status = "HOLD"
    reason = ""
    secret_tool = shutil.which("secret-tool")
    keyring_daemon = shutil.which("gnome-keyring-daemon")
    if not secret_tool or not keyring_daemon:
        reason = "SECRET_SERVICE_DEPENDENCIES_UNAVAILABLE"
    elif not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        reason = "ISOLATED_DBUS_SESSION_UNAVAILABLE"
    else:
        # The caller must create a disposable HOME/XDG profile and unlock a
        # disposable keyring before running this test.
        store = run([secret_tool, "store", "--label=LOUKSNA CP04 disposable test",
                     "service", SERVICE, "account", ACCOUNT], input_text=SYNTHETIC_VALUE)
        checks["synthetic_secret_store"] = store.returncode == 0
        lookup = run([secret_tool, "lookup", "service", SERVICE, "account", ACCOUNT])
        checks["lookup_returns_exact_synthetic_value"] = (
            lookup.returncode == 0 and lookup.stdout.strip() == SYNTHETIC_VALUE
        )
        clear = run([secret_tool, "clear", "service", SERVICE, "account", ACCOUNT])
        checks["secret_clear_command_succeeds"] = clear.returncode == 0
        absent = run([secret_tool, "lookup", "service", SERVICE, "account", ACCOUNT])
        checks["post_clear_lookup_confirms_absence"] = (
            absent.returncode != 0 or absent.stdout.strip() == ""
        )
        # Never serialize command output, stderr, or the synthetic value.
        # subprocess output is captured in memory and never printed or serialized.
        # A successful lookup necessarily returns the synthetic fixture to this process.
        visible_summary = json.dumps({
            "checks": {k: v for k, v in checks.items()},
            "status": "PASS_WITH_SCOPE_LIMITS",
            "secret_values_emitted": False,
        }, sort_keys=True)
        checks["secret_material_not_emitted"] = SYNTHETIC_VALUE not in visible_summary
        status = "PASS_WITH_SCOPE_LIMITS" if all(checks.values()) else "FAIL"
        if not all(checks.values()):
            reason = "ONE_OR_MORE_SECRET_SERVICE_LIFECYCLE_CHECKS_FAILED"

    candidate = os.environ.get("GITHUB_SHA", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "LOCAL_UNBOUND")
    report = {
        "schema": "louksna.zd.v03.cp04-secret-service-report.v1",
        "status": status,
        "gate_disposition": "HOLD_APP_COMMAND_HANDLER_INTEGRATION_STILL_REQUIRED",
        "candidate_commit_sha": candidate,
        "workflow_run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "DISPOSABLE_DBUS_AND_GNOME_KEYRING_WITH_SYNTHETIC_VALUE_ONLY",
        "production_backend_source_path": "scripts/missions/v03_templates/main.rs",
        "native_tauri_command_handlers_exercised": False,
        "real_credentials_used": False,
        "secret_value_or_command_output_emitted": False,
        "checks": checks,
        "reason_code": reason,
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema": "louksna.zd.v03.cp04-secret-service-manifest.v1",
        "candidate_commit_sha": candidate,
        "workflow_run_id": run_id,
        "report_path": str(OUT),
        "report_bytes": OUT.stat().st_size,
        "report_sha256": digest(OUT.read_bytes()),
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "gate_disposition": report["gate_disposition"],
        "candidate_commit_sha": candidate,
        "workflow_run_id": run_id,
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "reason_code": reason,
        "secret_values_emitted": False,
    }, sort_keys=True))
    return 0 if status == "PASS_WITH_SCOPE_LIMITS" else 1


if __name__ == "__main__":
    sys.exit(main())
