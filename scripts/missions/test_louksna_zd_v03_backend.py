#!/usr/bin/env python3
"""Static regression checks for security-sensitive V0.3 backend invariants."""
from pathlib import Path
import sys

source = Path(sys.argv[1] if len(sys.argv) > 1 else "scripts/missions/v03_templates/main.rs").read_text(encoding="utf-8")
checks = {
    "evidence_write_failure_is_visible": "LOUKSNA_EVIDENCE_WRITE_FAILED" in source,
    "credential_removal_is_verified": "SECRET_CLEAR_NOT_VERIFIED" in source and "secret_lookup()" in source,
    "remote_bridge_requires_https": 'parsed.scheme()!="https"' in source and ".https_only(true)" in source,
    "remote_bridge_has_bounded_timeout": "Duration::from_secs(20)" in source and "Duration::from_secs(5)" in source,
    "remote_response_size_is_bounded": "body.len().saturating_add(chunk.len()) > 200_000" in source and "body.len().saturating_add(chunk.len()) > 2_000_000" in source,
    "runtime_probe_can_report_degraded": '"DEGRADED"' in source and '"database_query"' in source,
    "offline_guard_remains": "if settings.offline_mode{return Err(\"OFFLINE_MODE_ENABLED\".into());}" in source,
    "github_reads_remain_api_backed": "https://api.github.com{}" in source,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'} {name}")
if failed:
    print("FAILED_CHECKS=" + ",".join(failed), file=sys.stderr)
    raise SystemExit(1)
print(f"V03_BACKEND_REGRESSION={len(checks)}/{len(checks)} PASS")
