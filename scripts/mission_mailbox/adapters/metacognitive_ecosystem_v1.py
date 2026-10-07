#!/usr/bin/env python3
"""Pinned admission adapter for MIS-META-ECO-20260928-V1.

Lightweight by design: verifies immutable mission/control-plane identities and
requires heavy material work to remain on GitHub-hosted or explicitly governed
external cloud compute. It performs no massive corpus/model/translation/market
work on the auxiliary self-hosted runner.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

MISSION_SHA256 = "1f8ba16e26789cc4ba3c9329357ac7c866af50177ccbf5915ca1dd5355c511d0"
MISSION_PATH = "missions/inbox/metacognitive-ecosystem-v1-20260928/MISSION_ORIGINAL.md"
MANIFEST_PATH = "ecosystem/metacognitive-operational-v1/CAPABILITIES.json"
MANIFEST_SHA256 = "9c4f33d0a31b3028b27185e3864cc839d88e34a32b09c2921370c116de9028ff"
CENSUS_PATH = "ecosystem/metacognitive-operational-v1/CUSTOSZ72_CENSUS.json"
DEDUP_EVIDENCE_PATH = "ecosystem/metacognitive-operational-v1/CUSTOSZ72_DEDUP_EVIDENCE.json"
DEDUP_VALIDATOR_PATH = "scripts/metacognitive/validate_custosz72_mcap59_dedup.py"
CENSUS_EXTRACTOR_PATH = "scripts/metacognitive/extract_custosz_v7_census.py"
EXPECTED = {
    "authority": "5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9",
    "custosz": "dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2",
    "runtime": "a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67",
    "metaos": "5d8f1239e3a0b452be722078760b000afc22af0a64f93ffb0a1f74024f15aed0",
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def utc():
    return datetime.now(timezone.utc).isoformat()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out")
    q = ap.parse_args()
    root = Path(q.repo_root).resolve()
    paths = {
        "mission": root / MISSION_PATH,
        "manifest": root / MANIFEST_PATH,
        "authority": root / "Louksna.md",
        "custosz": root / "artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz",
        "runtime": root / "artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz",
        "metaos": root / "artifacts/custosz-v7/MetaOS.wasm",
    }
    missing = [k for k, p in paths.items() if not p.is_file()]
    if missing:
        report = {
            "schema": "META_ECOSYSTEM_ADMISSION/1.0",
            "status": "HOLD",
            "root_blocker": "MISSING_REQUIRED_ARTIFACT",
            "missing": missing,
        }
    else:
        actual = {k: sha(v) for k, v in paths.items()}
        expected = {"mission": MISSION_SHA256, "manifest": MANIFEST_SHA256, **EXPECTED}
        mismatches = {
            k: {"expected": expected[k], "actual": actual[k]}
            for k in expected if actual[k] != expected[k]
        }
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        census_path = root / CENSUS_PATH
        dedup_evidence_path = root / DEDUP_EVIDENCE_PATH
        dedup_validator_path = root / DEDUP_VALIDATOR_PATH
        census_extractor_path = root / CENSUS_EXTRACTOR_PATH
        dedup_report = None
        dedup_error = None
        try:
            census = json.loads(census_path.read_text(encoding="utf-8"))
            census_ok = (
                census.get("capability_count") == 72
                and census.get("unique_capability_count") == 72
                and census.get("pyz_sha256") == actual["custosz"]
            )
            if not census_ok:
                raise RuntimeError("CUSTOSZ72_CENSUS_IDENTITY_OR_COUNT_MISMATCH")
            with tempfile.TemporaryDirectory(prefix="meta-dedup-") as td:
                dedup_out = Path(td) / "DEDUP.json"
                proc = subprocess.run([
                    sys.executable, "-B", "-I", str(dedup_validator_path),
                    "--manifest", str(paths["manifest"]),
                    "--evidence", str(dedup_evidence_path),
                    "--pyz", str(paths["custosz"]),
                    "--extractor", str(census_extractor_path),
                    "--out", str(dedup_out),
                ], capture_output=True, text=True, timeout=60)
                if proc.returncode != 0 or not dedup_out.is_file():
                    raise RuntimeError("DEDUP_VALIDATOR_FAILED:" + proc.stdout[-1000:] + proc.stderr[-1000:])
                dedup_report = json.loads(dedup_out.read_text(encoding="utf-8"))
                dedup_ok = (
                    dedup_report.get("status") == "PASS"
                    and dedup_report.get("g16_precheck") == "PASS"
                    and dedup_report.get("mapped_count") == 59
                    and dedup_report.get("custosz_capability_count") == 72
                )
        except Exception as exc:
            dedup_ok = False
            dedup_error = type(exc).__name__ + ":" + str(exc)[:2000]

        semantic_ok = (
            manifest.get("authority") == "Louksna.md"
            and manifest.get("capability_count") == 59
            and manifest.get("canonical_mutation") is False
            and manifest.get("authority_transfer") is False
            and manifest.get("failure_posture") == "FAIL_CLOSED"
            and manifest.get("training_last") is True
            and manifest.get("capabilities", [{}])[-1].get("name")
                == "GOVERNED_TRAINING_AND_CONTINUOUS_LEARNING"
        )
        status = "PASS" if not mismatches and semantic_ok and dedup_ok else "HOLD"
        report = {
            "schema": "META_ECOSYSTEM_ADMISSION/1.0",
            "utc": utc(),
            "status": status,
            "mission_sha256": MISSION_SHA256,
            "manifest_sha256": MANIFEST_SHA256,
            "identity_hashes": actual,
            "mismatches": mismatches,
            "semantic_contract_ok": semantic_ok,
            "custosz72_exact_census_ok": bool(locals().get("census_ok", False)),
            "g16_precheck": "PASS" if dedup_ok else "HOLD",
            "dedup_validation_summary": (
                {
                    "status": dedup_report.get("status"),
                    "mapped_count": dedup_report.get("mapped_count"),
                    "family9_action_counts": dedup_report.get("family9_action_counts"),
                    "failure_count": len(dedup_report.get("failures", [])),
                } if dedup_report else None
            ),
            "dedup_error": dedup_error,
            "execution_plane": "GITHUB_HOSTED_ONLY_OR_EXPLICIT_EXTERNAL_CLOUD",
            "auxiliary_runner_role": "INGRESS_ROUTING_AND_BOUNDED_ADMISSION_ONLY",
            "heavy_compute_on_auxiliary_runner": False,
            "canonical_mutation": False,
            "grants_g16": False,
            "grants_g23": False,
            "grants_g24": False,
            "next_gate": "CLOUD_CORE_MATERIALIZATION" if status == "PASS" else (
                "CUSTOSZ72_EXACT_DEDUP" if semantic_ok and not mismatches else "ADMISSION_REMEDIATION"
            ),
        }
    if q.out:
        out = Path(q.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 3

if __name__ == "__main__":
    raise SystemExit(main())
