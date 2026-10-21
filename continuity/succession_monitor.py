#!/usr/bin/env python3
"""Fail closed on a global certification claim, a D05 stall, or unsigned D07–D22 evidence."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def fail(reason: str) -> None:
    raise SystemExit("SUCCESSION_MONITOR_FAIL:" + reason)


def domain_of(cid: int) -> str:
    if cid <= 176:
        return "D05"
    if cid <= 230:
        return "D06"
    bounds = (
        (300, "D07"), (360, "D08"), (437, "D09"), (476, "D10"), (530, "D11"),
        (585, "D12"), (640, "D13"), (660, "D14"), (700, "D15"), (720, "D16"),
        (760, "D17"), (860, "D18"), (960, "D19"), (1000, "D20"), (1080, "D21"),
        (1200, "D22"),
    )
    for end, domain in bounds:
        if cid <= end:
            return domain
    fail(f"CAPABILITY_OUT_OF_RANGE:{cid}")


def main() -> int:
    state = load("continuity/STATE.json")
    if state.get("certified") is not False or state.get("global_certification_status") != "NOT_CERTIFIED":
        fail("GLOBAL_CERTIFICATION_ASSERTED")
    if state.get("next_point") == "D05" or state.get("block_reason") == "NEXT_D05_TRANCHE_EXECUTOR_NOT_REGISTERED":
        fail("STILL_STUCK_ON_D05")
    allowed = {f"D{n:02d}" for n in range(6, 23)} | {"NONE"}
    if state.get("active_domain") not in allowed:
        fail("ACTIVE_DOMAIN_NOT_ON_RAIL")
    registry = load("implementation/super1200/registry/capabilities.json")
    if registry.get("count") != 1200 or len(registry["items"]) != 1200:
        fail("REGISTRY_COUNT")
    by = {item["capability_id"]: item for item in registry["items"]}
    for cid in range(137, 231):
        item = by[cid]
        if item.get("implementation_state") != "EVIDENCED" or item.get("evidence_class") != "NAME_SPECIFIC":
            fail(f"MISSING_NAME_SPECIFIC:{cid}")
        domain = "D05" if cid <= 176 else "D06"
        ev = ROOT / "continuity/runtime-evidence" / domain / f"capability-{cid:04d}.json"
        if not ev.is_file():
            fail(f"MISSING_EVIDENCE:{cid}")
        body = json.loads(ev.read_text(encoding="utf-8"))
        if body.get("certification_granted") is not False:
            fail(f"EVIDENCE_SELF_CERTIFIED:{cid}")
    for cid in range(231, 1201):
        item = by[cid]
        if item.get("implementation_state") != "EVIDENCED" or item.get("evidence_class") != "NAME_SPECIFIC":
            fail(f"D07_PLUS_NOT_NAME_SPECIFIC:{cid}")
        ev = ROOT / "continuity/runtime-evidence" / domain_of(cid) / f"capability-{cid:04d}.json"
        if not ev.is_file():
            fail(f"MISSING_EVIDENCE:{cid}")
        body = json.loads(ev.read_text(encoding="utf-8"))
        if body.get("canonical_name") != item["canonical_name"]:
            fail(f"NAME_MISMATCH:{cid}")
        if body.get("certification_granted") is not False or body.get("global_certification_granted") is not False:
            fail(f"EVIDENCE_SELF_CERTIFIED:{cid}")
    kedb = ROOT / "continuity/KEDB_ENTRIES/D07_NAME_SPECIFIC_REQUIRED.json"
    if not kedb.is_file() or not json.loads(kedb.read_text())["next_action"]:
        fail("D07_HOLD_WITHOUT_NEXT_ACTION")
    proc = subprocess.run(
        [sys.executable, "-B", str(ROOT / "implementation/super1200/runtime/super1200_continuation_worker.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 78:
        fail("SYNTHETIC_MATERIALIZER_NOT_DISABLED")
    print("SUCCESSION_MONITOR_PASS active_domain=" + str(state.get("active_domain")) + " global=NOT_CERTIFIED synthetic=DISABLED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
