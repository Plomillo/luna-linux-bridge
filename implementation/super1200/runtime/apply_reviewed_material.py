#!/usr/bin/env python3
"""Materialize reviewed name-specific tranches. Never grants G23, G24, or global certification."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "implementation/super1200/registry/capabilities.json"
DOMAINS = ROOT / "implementation/super1200/registry/domains.json"
PROGRESS = ROOT / "implementation/super1200/DOMAIN_PROGRESS.json"
STATE = ROOT / "continuity/STATE.json"
EXECUTORS = ROOT / "continuity/EXECUTORS.json"

SPECS = {
    "D05": {
        "module": "implementation/super1200/domains/d05_137_176.py",
        "test": "implementation/super1200/tests/test_d05_137_176.py",
        "class_name": "D05RemainderTests",
        "start": 137,
        "end": 176,
    },
    "D06": {
        "module": "implementation/super1200/domains/d06_177_230.py",
        "test": "implementation/super1200/tests/test_d06_177_230.py",
        "class_name": "D06Tests",
        "start": 177,
        "end": 230,
    },
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tranches(domain_id: str) -> list[tuple[int, int]]:
    meta = next(item for item in load(DOMAINS)["items"] if item["domain_id"] == domain_id)
    out = []
    cursor = meta["from"]
    while cursor <= meta["to"]:
        end = min(meta["to"], cursor + 3)
        out.append((cursor, end))
        cursor = end + 1
    return out


def run_test(spec: dict, cid: int) -> None:
    test_name = f"{spec['class_name']}.test_cap_{cid:04d}"
    proc = subprocess.run(
        [sys.executable, "-B", str(ROOT / spec["test"]), "-v", test_name],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )
    output = proc.stdout + "\n" + proc.stderr
    ok = proc.returncode == 0 and f"test_cap_{cid:04d}" in output and "Ran 1 test" in output and "\nOK" in output and "FAILED" not in output
    if not ok:
        print(output[-4000:])
        raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_TEST_FAIL capability={cid}")


def mark(item: dict, spec: dict) -> None:
    item["implementation_state"] = "EVIDENCED"
    item["implementation_artifact"] = spec["module"]
    item["test_artifact"] = spec["test"]
    item["materialization"] = "CODE+NAME_SPECIFIC_BEHAVIOR+PER_CAPABILITY_NEGATIVE_TEST+HASH_BOUND_EVIDENCE"
    item["theorem_claim_from_type_checking"] = False
    item["evidence_class"] = "NAME_SPECIFIC"


def apply_domain(domain_id: str) -> list[str]:
    spec = SPECS[domain_id]
    registry = load(REGISTRY)
    domain = load(ROOT / f"implementation/super1200/domains/{domain_id}.json")
    by_reg = {item["capability_id"]: item for item in registry["items"]}
    by_dom = {item["capability_id"]: item for item in domain["capabilities"]}
    module_path = ROOT / spec["module"]
    test_path = ROOT / spec["test"]
    sys.path.insert(0, str(module_path.parent))
    import importlib.util

    loaded = importlib.util.spec_from_file_location(domain_id.lower() + "_reviewed", module_path)
    module = importlib.util.module_from_spec(loaded)
    assert loaded and loaded.loader
    loaded.loader.exec_module(module)
    checkpoints = []
    evidence_dir = ROOT / "continuity/runtime-evidence" / domain_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    module_hash = sha(module_path)
    test_hash = sha(test_path)
    for start, end in tranches(domain_id):
        if end < spec["start"] or start > spec["end"]:
            continue
        ids = list(range(max(start, spec["start"]), min(end, spec["end"]) + 1))
        for cid in ids:
            name, _fn = module.FUNCS[cid]
            if by_reg[cid]["canonical_name"] != name or by_dom[cid]["canonical_name"] != name:
                raise SystemExit(f"SUPER1200_TELEMETRY IDENTITY_MISMATCH {cid}")
            run_test(spec, cid)
            evidence = {
                "schema": "SUPER1200_REVIEWED_TRANCHE_EVIDENCE/1",
                "capability_id": cid,
                "canonical_name": name,
                "domain_id": domain_id,
                "executor": "implementation/super1200/runtime/apply_reviewed_material.py",
                "implementation_artifact": spec["module"],
                "test_artifact": spec["test"],
                "test_case": f"test_cap_{cid:04d}",
                "status": "PASS",
                "module_sha256": module_hash,
                "test_sha256": test_hash,
                "evidence_class": "NAME_SPECIFIC",
                "theorem_claim_from_type_checking": False,
                "certification_granted": False,
                "global_certification_granted": False,
                "g23": "PENDING_INDEPENDENT_VALIDATION",
                "g24": "PENDING_G23",
                "validated_at_utc": now,
            }
            evidence["evidence_sha256"] = hashlib.sha256(
                json.dumps({k: v for k, v in evidence.items() if k != "evidence_sha256"}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest()
            (evidence_dir / f"capability-{cid:04d}.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            mark(by_reg[cid], spec)
            mark(by_dom[cid], spec)
        checkpoints.append(f"{domain_id}_{ids[0]}_{ids[-1]}_MATERIALIZED")
    if all(by_dom[cid]["implementation_state"] == "EVIDENCED" for cid in range(domain["range"][0], domain["range"][1] + 1)):
        domain["state"] = "FUNCTIONALLY_CLOSED_PENDING_INDEPENDENT_VALIDATION"
    domain["terminal_certification"] = False
    dump(ROOT / f"implementation/super1200/domains/{domain_id}.json", domain)
    dump(REGISTRY, registry)
    return checkpoints


def main() -> int:
    state = load(STATE)
    active = str(state.get("active_domain", ""))
    checkpoint = str(state.get("current_checkpoint", ""))
    if active in {f"D{n:02d}" for n in range(7, 23)} or checkpoint.startswith(tuple(f"D{n:02d}" for n in range(7, 23))):
        print("SUPER1200_TELEMETRY REFUSE_REWIND active=" + active + " checkpoint=" + checkpoint)
        return 78
    if load(REGISTRY).get("count") != 1200:
        raise SystemExit("DENY_REGISTRY_COUNT")
    d05_cps = apply_domain("D05")
    d06_cps = apply_domain("D06")
    progress = load(PROGRESS)
    for item in progress["domains"]:
        if item["domain_id"] in {"D05", "D06"}:
            item["state"] = "FUNCTIONALLY_CLOSED_PENDING_INDEPENDENT_VALIDATION"
    progress["terminal_certification"] = False
    dump(PROGRESS, progress)
    state = load(STATE)
    state.update({
        "active_worker": False,
        "blocked": True,
        "block_reason": "NEXT_D07_TRANCHE_EXECUTOR_NOT_REGISTERED",
        "blocked_at": datetime.now(timezone.utc).isoformat(),
        "certified": False,
        "current_checkpoint": d06_cps[-1],
        "diagnostic": (
            "D05 137-176 and D06 177-230 are name-specific and materialized. "
            "Scoped G23/G24 for those tranches remain PENDING until the independent succession gate re-runs the tests. "
            "D07 is not entered: no reviewed executor exists, and the synthetic materializer stays disabled. "
            "Global SUPER1200 certification remains NOT_CERTIFIED."
        ),
        "g23": "PENDING_FOR_SCOPE_D05_137_140",
        "g24": "PENDING_G23",
        "global_certification_status": "NOT_CERTIFIED",
        "next_point": "D07",
        "next_worker": None,
        "status": "BLOCKED",
        "material_checkpoints": d05_cps + d06_cps,
    })
    state["last_execution"] = {
        "status": "COMPLETED_SUCCESS_MATERIAL_TRANCHE",
        "material_capabilities": list(range(137, 231)),
        "executor": "implementation/super1200/runtime/apply_reviewed_material.py",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "g23": "PENDING",
        "g24": "PENDING_G23",
        "global_certification_status": "NOT_CERTIFIED",
    }
    dump(STATE, state)
    executors = load(EXECUTORS)
    executors["executors"]["D05"] = "implementation/super1200/runtime/apply_reviewed_material.py"
    executors["executors"]["D06"] = "implementation/super1200/runtime/apply_reviewed_material.py"
    executors["missing_executor_state"] = "D07"
    executors["reconciliation"] = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "D05_D06_NAME_SPECIFIC_MATERIALIZED_D07_EXECUTOR_ABSENT",
        "policy": "FAIL_CLOSED",
        "note": "Reviewed executors for D05 137-176 and D06 177-230 ran their negative tests. D07 was not invented. Global certification remains NOT_CERTIFIED.",
    }
    executors["domain_executor_history"].append({
        "domain": "D05",
        "executor": "implementation/super1200/runtime/apply_reviewed_material.py",
        "capabilities": list(range(137, 177)),
        "status": "MATERIALIZED_G23_PENDING",
        "global_certification": False,
    })
    executors["domain_executor_history"].append({
        "domain": "D06",
        "executor": "implementation/super1200/runtime/apply_reviewed_material.py",
        "capabilities": list(range(177, 231)),
        "status": "MATERIALIZED_G23_PENDING",
        "global_certification": False,
    })
    dump(EXECUTORS, executors)
    print("SUPER1200_TELEMETRY " + json.dumps({
        "event": "D05_CLOSED_D06_ENTERED",
        "d05_checkpoint": d05_cps[-1],
        "d06_checkpoint": d06_cps[-1],
        "next_point": "D07",
        "certification_granted": False,
        "global_certification_status": "NOT_CERTIFIED",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
