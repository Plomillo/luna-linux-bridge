#!/usr/bin/env python3
"""Produce digest-bound evidence for the bounded, isolated Runtime V1 integration probe."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from custoszv8.core import RuntimeV1Adapter, RUNTIME_V1_SELECTED_SHA256

RUNTIME = ROOT / "artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> int:
    report = {
        "schema": "custoszv8.runtime-v1-bounded-integration.v1",
        "candidate_commit": os.environ.get("CUSTOSZV8_CANDIDATE_SHA") or os.environ.get("GITHUB_SHA", "LOCAL_UNBOUND"),
        "observed_at_utc": now(),
        "runtime_path": str(RUNTIME.relative_to(ROOT)),
        "expected_runtime_sha256": RUNTIME_V1_SELECTED_SHA256,
        "status": "HOLD",
        "g23": "NOT_GRANTED",
        "g24": "NOT_GRANTED",
        "certification": "NOT_GRANTED",
        "execution_authorized": False,
        "mission_dispatch_enabled": False,
        "limitations": [
            "The authority supplied to this probe is synthetic and is not Louksna.md.",
            "The probe checks Runtime.selftest, one sandbox-file checkpoint/restore round trip, one benign bounded ProcessSupervisor child, and wrong-authority fail-closed behavior.",
            "SRExecBoundFME01 material mission dispatch is not invoked.",
            "This is not a production restore, global non-regression proof, independent G23 validation, or G24 certification."
        ],
    }
    try:
        if not RUNTIME.is_file():
            raise RuntimeError("selected Runtime V1 archive is missing")
        report["runtime_size_bytes"] = RUNTIME.stat().st_size
        report["runtime_observed_sha256"] = __import__("hashlib").sha256(RUNTIME.read_bytes()).hexdigest()
        adapter = RuntimeV1Adapter(RUNTIME_V1_SELECTED_SHA256, native_interface_verified=False)
        result = adapter.invoke(
            RuntimeV1Adapter.BOUNDED_PROBE_ID,
            RUNTIME,
            "CI-BOUNDED-RUNTIME-V1-INTEGRATION",
            explicit_opt_in=True,
        )
        report["probe"] = result
        required_passes = (
            result.get("status") == "PASS_BOUNDED_RUNTIME_V1_INTEGRATION"
            and result.get("runtime_sha256") == RUNTIME_V1_SELECTED_SHA256
            and result.get("checkpoint_roundtrip", {}).get("status") == "PASS"
            and result.get("process_supervisor", {}).get("status") == "PASS"
            and result.get("fail_closed_wrong_authority", {}).get("status") == "PASS"
            and result.get("journal_verified") is True
            and result.get("canonical_authority_binding") == "NOT_TESTED_SYNTHETIC_FIXTURE_ONLY"
            and result.get("mission_dispatch") == "NOT_PERFORMED"
            and result.get("SRExecBoundFME01") == "NOT_INVOKED"
            and result.get("execution_authorized") is False
            and result.get("g23") == "NOT_GRANTED"
            and result.get("g24") == "NOT_GRANTED"
        )
        if not required_passes:
            raise RuntimeError("bounded probe did not satisfy every expected assertion")
        report["status"] = "PASS_BOUNDED_RUNTIME_V1_INTEGRATION"
        report["production_native_interface_verified"] = False
        report["gates"] = {
            "bounded_api_selftest": "PASS",
            "sandbox_checkpoint_restore": "PASS",
            "bounded_process_supervisor": "PASS",
            "wrong_authority_fail_closed": "PASS",
            "canonical_louksna_binding": "NOT_TESTED",
            "sr_exec_bound_fme_01_mission_dispatch": "NOT_TESTED",
            "production_restore": "NOT_TESTED",
            "G22": "NOT_DEMONSTRATED",
            "G23": "NOT_GRANTED",
            "G24": "NOT_GRANTED",
        }
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
    out = ROOT / "evidence/custoszv8-runtime-v1-integration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS_BOUNDED_RUNTIME_V1_INTEGRATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
