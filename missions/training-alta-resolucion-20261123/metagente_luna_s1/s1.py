"""S1 entry. Interprets one operation and executes only a ready plan."""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

from metagente_luna_s1.pipeline import execute_plan, plan_for

IDENTITY = json.loads((Path(__file__).with_name("identity.json")).read_text(encoding="utf-8"))


def execute(instruction: str, predecessor: str | None = None) -> dict:
    plan = plan_for(instruction, predecessor)
    plan = execute_plan(plan)
    plan["agent"] = IDENTITY["AGENT_ID"]
    plan["version"] = IDENTITY["AGENT_VERSION"]
    plan["machinery"] = IDENTITY["MACHINERY"]
    if not plan.get("reason"):
        plan["reason"] = "MISSING_REASON"
        plan["status"] = "ERROR"
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="metagente-luna-s1")
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--predecessor", default="")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        result = execute(args.instruction, args.predecessor or None)
        code = 0 if result["status"] == "READY" else 2
    except Exception:
        result = {"status": "ERROR", "stage": "UNCAUGHT", "reason": "EXCEPTION", "detail": traceback.format_exc()[-800:], "machinery": "S1"}
        code = 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
    state = Path(args.state_dir)
    state.mkdir(parents=True, exist_ok=True)
    with (state / "journal.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"status": result["status"], "stage": result.get("stage"), "reason": result.get("reason"), "capability": result.get("capability")}, ensure_ascii=False) + "\n")
    sys.stdout.write(result["status"] + " " + result.get("reason", "") + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
