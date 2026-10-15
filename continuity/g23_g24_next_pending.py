#!/usr/bin/env python3
"""Independent scoped G23/G24 for the oldest pending reviewed tranche.

One scope per invocation. Never grants global SUPER1200 certification.
GATE_STAGE=G23 validates and writes g23-validation.json.
GATE_STAGE=G24 revalidates.
GATE_STAGE=PERSIST writes the scoped certificate and STATE pointer only.
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
MANIFEST = ROOT / "continuity/REVIEWED_TRANCHES.json"
STATE = ROOT / "continuity/STATE.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deny(reason: str) -> None:
    raise SystemExit("SUCCESSION_GATE_DENY:" + reason)


def scope_of(tranche: dict) -> str:
    return f"{tranche['domain_id']}:{tranche['from']}-{tranche['to']}"


def cert_path(tranche: dict) -> Path:
    return ROOT / "continuity/certification" / f"{tranche['domain_id']}_{tranche['from']}_{tranche['to']}.json"


def certified(tranche: dict) -> bool:
    path = cert_path(tranche)
    if not path.is_file():
        return False
    cert = load(path)
    return cert.get("result") == "PASS" and cert.get("scope") == scope_of(tranche) and cert.get("global_super1200_certified") is False and cert.get("certification_granted") is True


def oldest_pending() -> dict | None:
    for tranche in load(MANIFEST)["tranches"]:
        if not certified(tranche):
            return tranche
    return None


def revalidate(tranche: dict) -> dict:
    registry = load(ROOT / "implementation/super1200/registry/capabilities.json")
    by = {item["capability_id"]: item for item in registry["items"]}
    module = ROOT / tranche["module"]
    test = ROOT / tranche["test"]
    if not module.is_file() or not test.is_file():
        deny("MISSING_ARTIFACT")
    module_hash = sha(module)
    test_hash = sha(test)
    evidence = []
    for cid in range(tranche["from"], tranche["to"] + 1):
        item = by[cid]
        if item.get("implementation_state") != "EVIDENCED":
            deny(f"NOT_EVIDENCED:{cid}")
        if item.get("evidence_class") != "NAME_SPECIFIC":
            deny(f"NOT_NAME_SPECIFIC:{cid}")
        ev_path = ROOT / "continuity/runtime-evidence" / tranche["domain_id"] / f"capability-{cid:04d}.json"
        if not ev_path.is_file():
            deny(f"MISSING_EVIDENCE:{cid}")
        ev = load(ev_path)
        if ev.get("canonical_name") != item["canonical_name"]:
            deny(f"NAME_MISMATCH:{cid}")
        if ev.get("certification_granted") is not False or ev.get("global_certification_granted") is not False:
            deny(f"CERT_FLAG:{cid}")
        if ev.get("module_sha256") != module_hash or ev.get("test_sha256") != test_hash:
            deny(f"HASH_MISMATCH:{cid}")
        test_name = f"{tranche['class_name']}.test_cap_{cid:04d}"
        proc = subprocess.run([sys.executable, "-B", str(test), "-v", test_name], cwd=ROOT, text=True, capture_output=True, timeout=120)
        output = proc.stdout + "\n" + proc.stderr
        if proc.returncode != 0 or "Ran 1 test" not in output or "\nOK" not in output:
            print(output[-4000:])
            deny(f"TEST:{cid}")
        evidence.append({"capability_id": cid, "evidence_sha256": ev["evidence_sha256"], "canonical_name": item["canonical_name"]})
    return {
        "scope": scope_of(tranche),
        "result": "PASS",
        "module_sha256": module_hash,
        "test_sha256": test_hash,
        "evidence": evidence,
        "global_super1200_certified": False,
        "theorem_claim_from_type_checking": False,
    }


def persist(tranche: dict, report: dict) -> None:
    state = load(STATE)
    if state.get("certified") is not False or state.get("global_certification_status") != "NOT_CERTIFIED":
        deny("GLOBAL_FLAG")
    record = {
        "schema": "SUPER1200_G24_CERTIFICATION_DECISION/1",
        "basis": "G23_PASS_PLUS_INDEPENDENT_G24_SOURCE_REVALIDATION",
        "result": "PASS",
        "scope": report["scope"],
        "scope_only": True,
        "certification_granted": True,
        "global_super1200_certified": False,
        "g23": "PASS",
        "g24": "PASS",
        "g23_workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "g24_workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "module_sha256": report["module_sha256"],
        "test_sha256": report["test_sha256"],
        "evidence": report["evidence"],
        "theorem_claim_from_type_checking": False,
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    cert_path(tranche).parent.mkdir(parents=True, exist_ok=True)
    cert_path(tranche).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    state.setdefault("scoped_certifications", {})[report["scope"]] = {
        "scope": report["scope"],
        "status": "PASS",
        "record_path": str(cert_path(tranche).relative_to(ROOT)),
        "certification_granted": True,
        "global_certification_granted": False,
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    nxt = oldest_pending()
    state["certified"] = False
    state["global_certification_status"] = "NOT_CERTIFIED"
    state["active_domain"] = "D06"
    state["synthetic_materializer"] = "DISABLED"
    state["d07_executor"] = "NOT_REGISTERED"
    if nxt is None:
        state["g23"] = "REVIEWED_SCOPES_CERTIFIED"
        state["g24"] = "REVIEWED_SCOPES_CERTIFIED"
        state["block_reason"] = "NEXT_D07_TRANCHE_EXECUTOR_NOT_REGISTERED"
        state["status"] = "BLOCKED"
        state["next_point"] = "D07"
    else:
        token = scope_of(nxt).replace(":", "_")
        state["g23"] = "PENDING_FOR_SCOPE_" + token
        state["g24"] = "PENDING_G23"
        state["block_reason"] = "SCOPED_G23_PENDING_" + token
        state["status"] = "G23_PENDING"
        state["next_point"] = "D06"
    state["blocked"] = True
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    stage = os.environ.get("GATE_STAGE", "G23")
    tranche = oldest_pending()
    if tranche is None:
        print("SUCCESSION_GATE_IDLE no pending reviewed scope")
        Path("g23-validation.json").write_text(json.dumps({"result": "IDLE", "global_super1200_certified": False}) + "\n")
        return 0
    report = revalidate(tranche)
    if stage == "G23":
        Path("g23-validation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
                handle.write("result=PASS\n")
                handle.write("scope=" + report["scope"] + "\n")
        print("SUCCESSION_G23_PASS " + report["scope"])
        return 0
    if stage == "G24":
        Path("g24-certification-decision.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("SUCCESSION_G24_PASS " + report["scope"])
        return 0
    if stage == "PERSIST":
        persist(tranche, report)
        print("SUCCESSION_PERSIST_PASS " + report["scope"] + " GLOBAL_CERTIFICATION=FALSE")
        return 0
    deny("UNKNOWN_STAGE")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
