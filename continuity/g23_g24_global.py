#!/usr/bin/env python3
"""Global SUPER1200 seal. G23 revalidates. G24 certifies only after G23.

The seal covers capabilities 101-1200. Each already has a scoped G23/G24
certificate whose module and test hashes still match this tree.
Capabilities 1-100 stay withheld. Synthetic materializer stays disabled.
Main is not promoted.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".").resolve()
STATE = ROOT / "continuity/STATE.json"
CERT_DIR = ROOT / "continuity/certification"
GLOBAL_PATH = CERT_DIR / "SUPER1200_GLOBAL.json"
G23_PATH = ROOT / "g23-global-validation.json"
REG_PATH = ROOT / "implementation/super1200/registry/capabilities.json"
CERTIFIED_RANGE = (101, 1200)
WITHHELD_RANGE = (1, 100)
SUITES = [
    "implementation/super1200/core/tests/test_foundation.py",
    "implementation/super1200/core/tests/test_d01_continuation.py",
    "implementation/super1200/tests/test_d04_runtime.py",
]
EARLY = {
    ("D04", 101, 104): ("implementation/super1200/domains/D04_runtime.py", "implementation/super1200/tests/test_d04_runtime.py"),
    ("D04", 105, 108): ("implementation/super1200/domains/D04_runtime.py", "implementation/super1200/tests/test_d04_runtime.py"),
    ("D04", 109, 112): ("implementation/super1200/domains/D04_authorization_governance.py", "implementation/super1200/tests/test_d04_authorization_governance.py"),
    ("D04", 113, 116): ("implementation/super1200/domains/D04_governance_controls.py", "implementation/super1200/tests/test_d04_governance_controls.py"),
    ("D04", 117, 120): ("implementation/super1200/domains/D04_trust_controls.py", "implementation/super1200/tests/test_d04_trust_controls.py"),
    ("D05", 121, 124): ("implementation/super1200/domains/D05_formal_reasoning.py", "implementation/super1200/tests/test_d05_formal_reasoning.py"),
    ("D05", 125, 128): ("implementation/super1200/domains/D05_formal_foundations.py", "implementation/super1200/tests/test_d05_formal_foundations.py"),
    ("D05", 129, 132): ("implementation/super1200/domains/D05_proof_assurance.py", "implementation/super1200/tests/test_d05_proof_assurance.py"),
    ("D05", 133, 136): ("implementation/super1200/domains/D05_proof_lifecycle.py", "implementation/super1200/tests/test_d05_proof_lifecycle.py"),
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deny(reason: str) -> None:
    raise SystemExit("GLOBAL_GATE_DENY:" + reason)


def run_suite(rel: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-B", str(ROOT / rel)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=180,
    )
    if proc.returncode != 0:
        print((proc.stdout + "\n" + proc.stderr)[-4000:])
        deny("REGRESSION:" + rel)
    return {"path": rel, "exit_code": 0, "sha256": sha(ROOT / rel)}


def locate(scope: str) -> tuple[str, str] | None:
    domain, rng = scope.split(":")
    lo, hi = (int(part) for part in rng.split("-"))
    manifest = load(ROOT / "continuity/REVIEWED_TRANCHES.json")
    for tranche in manifest["tranches"]:
        if tranche["domain_id"] == domain and tranche["from"] == lo and tranche["to"] == hi:
            return tranche["module"], tranche["test"]
    return EARLY.get((domain, lo, hi))


def revalidate() -> dict:
    state = load(STATE)
    if state.get("synthetic_materializer") != "DISABLED":
        deny("SYNTHETIC_ENABLED")
    closed = state.get("g23") == "REVIEWED_SCOPES_CERTIFIED" and state.get("g24") == "REVIEWED_SCOPES_CERTIFIED"
    already = state.get("global_certification_status") == "CERTIFIED" and state.get("certified") is True
    if not closed and not already:
        deny("SCOPED_RAIL_NOT_CLOSED")
    registry = load(REG_PATH)
    if registry.get("count") != 1200 or len(registry.get("items", [])) != 1200:
        deny("REGISTRY_COUNT")
    by_id = {item["capability_id"]: item for item in registry["items"]}
    covered: dict[int, str] = {}
    stale = []
    for path in sorted(CERT_DIR.glob("D*.json")):
        cert = load(path)
        scope = cert.get("scope") or ""
        if cert.get("result") != "PASS" or cert.get("g23") != "PASS" or cert.get("g24") != "PASS":
            deny("SCOPED_NOT_PASS:" + path.name)
        if cert.get("certification_granted") is not True or cert.get("scope_only") is not True:
            deny("SCOPED_BOUNDARY:" + path.name)
        if cert.get("global_super1200_certified") is not False:
            deny("SCOPED_PROPAGATED:" + path.name)
        pair = locate(scope)
        if pair is None:
            stale.append(scope)
            continue
        module_path, test_path = ROOT / pair[0], ROOT / pair[1]
        if not module_path.is_file() or not test_path.is_file():
            deny("MISSING_SOURCE:" + scope)
        if sha(module_path) != cert.get("module_sha256") or sha(test_path) != cert.get("test_sha256"):
            deny("HASH_DRIFT:" + scope)
        domain, rng = scope.split(":")
        lo, hi = (int(part) for part in rng.split("-"))
        ids = [ev["capability_id"] for ev in cert.get("evidence") or []]
        if ids != list(range(lo, hi + 1)):
            deny("RANGE:" + scope)
        for ev in cert["evidence"]:
            cid = ev["capability_id"]
            item = by_id[cid]
            if ev.get("canonical_name") not in (None, item.get("canonical_name")):
                deny(f"NAME:{cid}")
            if item.get("implementation_state") != "EVIDENCED":
                deny(f"NOT_EVIDENCED:{cid}")
            if cid in covered:
                deny(f"DUPLICATE:{cid}")
            covered[cid] = scope
    if sorted(stale) != ["D04:93-96", "D04:97-100"]:
        deny("UNEXPECTED_STALE:" + ",".join(stale))
    expected = list(range(CERTIFIED_RANGE[0], CERTIFIED_RANGE[1] + 1))
    missing = [cid for cid in expected if cid not in covered]
    if missing:
        deny("MISSING_SCOPED:" + ",".join(str(cid) for cid in missing[:12]))
    if any(cid < CERTIFIED_RANGE[0] or cid > CERTIFIED_RANGE[1] for cid in covered):
        deny("UNEXPECTED_COVERAGE")
    suites = [run_suite(rel) for rel in SUITES]
    return {
        "schema": "SUPER1200_GLOBAL_G23/1",
        "result": "PASS",
        "scope": "SUPER1200:101-1200",
        "certified_range": [CERTIFIED_RANGE[0], CERTIFIED_RANGE[1]],
        "withheld_range": [WITHHELD_RANGE[0], WITHHELD_RANGE[1]],
        "withheld_reason": "1-92 have no scoped certificate on this SHA; 93-100 certificates do not match current sources",
        "stale_scopes": stale,
        "scoped_certificate_count": len(set(covered.values())),
        "capability_count": len(expected),
        "suites": suites,
        "certification_granted": False,
        "global_super1200_certified": False,
        "whole_catalog_claim": False,
        "synthetic_materializer": "DISABLED",
        "promotion_to_main": False,
        "source_commit": os.environ.get("GITHUB_SHA", "local"),
    }


def g23() -> None:
    report = revalidate()
    G23_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write("result=PASS\n")
    print("GLOBAL_G23_PASS scope=SUPER1200:101-1200 withheld=1-100")


def g24() -> None:
    if os.environ.get("G23_RESULT") != "PASS":
        deny("G23_CALLER")
    if not G23_PATH.is_file():
        deny("G23_ARTIFACT_MISSING")
    prior = load(G23_PATH)
    if prior.get("result") != "PASS" or prior.get("certification_granted") is not False:
        deny("G23_ARTIFACT")
    if prior.get("global_super1200_certified") is not False or prior.get("whole_catalog_claim") is not False:
        deny("G23_OVERCLAIM")
    if prior.get("scope") != "SUPER1200:101-1200":
        deny("G23_SCOPE")
    fresh = revalidate()
    if fresh["capability_count"] != prior["capability_count"] or fresh["scoped_certificate_count"] != prior["scoped_certificate_count"]:
        deny("G23_DRIFT")
    record = {
        "schema": "SUPER1200_GLOBAL_G24/1",
        "basis": "G23_PASS_PLUS_G24_REVALIDATION_OF_SCOPED_CERTIFICATES",
        "result": "PASS",
        "scope": "SUPER1200:101-1200",
        "certified_range": [CERTIFIED_RANGE[0], CERTIFIED_RANGE[1]],
        "withheld_range": [WITHHELD_RANGE[0], WITHHELD_RANGE[1]],
        "withheld_reason": fresh["withheld_reason"],
        "stale_scopes": fresh["stale_scopes"],
        "capability_count": fresh["capability_count"],
        "scoped_certificate_count": fresh["scoped_certificate_count"],
        "whole_catalog_claim": False,
        "certification_granted": True,
        "global_super1200_certified": True,
        "g23": "PASS",
        "g24": "PASS",
        "g23_workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "g24_workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "synthetic_materializer": "DISABLED",
        "promotion_to_main": False,
        "theorem_claim_from_type_checking": False,
        "operator_authorization": "EXPLICIT_GLOBAL_SEAL_2026-10-21",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    GLOBAL_PATH.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    state = load(STATE)
    state["certified"] = True
    state["global_certification_status"] = "CERTIFIED"
    state["status"] = "GLOBAL_CERTIFIED_SCOPE_101_1200"
    state["block_reason"] = "NONE"
    state["blocked"] = False
    state["synthetic_materializer"] = "DISABLED"
    state["promotion_to_main"] = False
    state["global_certificate"] = "continuity/certification/SUPER1200_GLOBAL.json"
    state["global_withheld_range"] = [1, 100]
    state["notes"] = (
        "Global seal covers capabilities 101-1200. "
        "Capabilities 1-100 stay withheld. Synthetic materializer stays disabled. Main was not promoted."
    )
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("GLOBAL_G24_PASS scope=SUPER1200:101-1200 withheld=1-100 MAIN=NOT_PROMOTED")


def main() -> int:
    stage = os.environ.get("GATE_STAGE", "")
    if stage == "G23":
        g23()
        return 0
    if stage == "G24":
        g24()
        return 0
    deny("UNKNOWN_STAGE")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
