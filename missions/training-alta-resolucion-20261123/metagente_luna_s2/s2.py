"""S2 entry. Refuses to run if the pinned sources are absent or altered."""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metagente_luna.m0 import execute as m0_execute
from metagente_luna.parse import Unmatched
from metagente_luna_s2.engine import EXECUTORS, select
from metagente_luna_s2.preflight import check

IDENTITY = json.loads((Path(__file__).with_name("identity.json")).read_text(encoding="utf-8"))


def execute(instruction: str, predecessor: str | None, criterion: str, mission_root: Path) -> dict:
    gate = check(mission_root)
    if not gate["ok"]:
        return {"status": "BLOCKED", "stage": "PREFLIGHT", "reason": gate["reason"], "machinery": IDENTITY["MACHINERY"], "primary_cause": "MISSING_AUTHORITY_DOCUMENT"}
    chosen = select(instruction, predecessor, criterion)
    if chosen is None:
        try:
            delegated = m0_execute(" ".join(instruction.split()))
        except Unmatched:
            return {"status": "NO_CAPABILITY", "stage": "CAPABILITY_SELECTION", "reason": "NO_REGISTERED_CAPABILITY", "primary_cause": "MISSING_CAPABILITY", "m0_immediate_cause": "PARSER_RECOGNITION_FAILURE", "machinery": IDENTITY["MACHINERY"]}
        return {"status": "READY", "stage": "DELEGATED_TO_M0", "reason": "M0_GRAMMAR_MATCH", "capability": "baseline_m0", "observed": delegated.get("observed"), "delegated_to": "M0-20261124.2", "machinery": IDENTITY["MACHINERY"]}
    if "stop" in chosen:
        return {"status": chosen["stop"], "stage": chosen["stage"], "reason": chosen["reason"], "primary_cause": chosen.get("primary_cause"), "machinery": IDENTITY["MACHINERY"]}
    observed = EXECUTORS[chosen["capability"]](**chosen["call"])
    return {
        "status": "READY",
        "stage": "EXECUTED",
        "reason": chosen["reason"],
        "capability": chosen["capability"],
        "limit": chosen.get("limit"),
        "accredited_by_selector": chosen.get("accredited", True),
        "observed": observed,
        "machinery": IDENTITY["MACHINERY"],
        "version": IDENTITY["AGENT_VERSION"],
        "learning": "NOT_DEMONSTRATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="metagente-luna-s2")
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--predecessor", default="")
    parser.add_argument("--criterion", default="")
    parser.add_argument("--mission-root", default=os.environ.get("MISSION_ROOT", ""))
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        result = execute(args.instruction, args.predecessor or None, args.criterion, Path(args.mission_root))
        code = 0 if result["status"] == "READY" else 2
    except Exception:
        result = {"status": "ERROR", "stage": "UNCAUGHT", "reason": "EXCEPTION", "detail": traceback.format_exc()[-800:], "machinery": "S2"}
        code = 1
    if not result.get("reason"):
        result["reason"] = "MISSING_REASON"
        code = 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(args.state_dir).mkdir(parents=True, exist_ok=True)
    sys.stdout.write(result["status"] + " " + str(result.get("capability") or result["reason"]) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
