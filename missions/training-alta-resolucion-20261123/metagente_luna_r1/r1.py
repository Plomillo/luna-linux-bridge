"""Derived dispatcher. M0 is called and never modified."""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metagente_luna.m0 import execute as m0_execute
from metagente_luna.parse import Unmatched

from metagente_luna_r1.dispatch import recognize, run

IDENTITY = json.loads((Path(__file__).with_name("identity.json")).read_text(encoding="utf-8"))


def _base(instruction: str, status: str, stage: str, reason: str) -> dict:
    return {
        "agent": IDENTITY["AGENT_ID"],
        "version": IDENTITY["AGENT_VERSION"],
        "machinery": IDENTITY["MACHINERY"],
        "instruction": instruction,
        "status": status,
        "stage": stage,
        "reason": reason,
    }


def execute(instruction: str, predecessor: str | None = None) -> dict:
    text = " ".join(instruction.split())
    try:
        delegated = m0_execute(text)
    except Unmatched:
        delegated = None
    except Exception as exc:
        return _base(instruction, "ERROR", "M0_DELEGATION", type(exc).__name__) | {"detail": traceback.format_exc()[-500:]}
    if delegated is not None:
        delegated["machinery"] = IDENTITY["MACHINERY"]
        delegated["version"] = IDENTITY["AGENT_VERSION"]
        delegated["delegated_to"] = "M0-20261124.2"
        delegated["stage"] = "DELEGATED_TO_M0"
        delegated["reason"] = "M0_GRAMMAR_MATCH"
        return delegated
    call = recognize(text, predecessor)
    if call is None:
        return _base(instruction, "UNMATCHED", "RECOGNITION", "NO_GRAMMAR_MATCH")
    if "stop" in call:
        return _base(instruction, call["stop"], call["stage"], call["reason"])
    observed = run(call)
    result = _base(instruction, "OBSERVED", "EXECUTED", "TOOL_RETURNED")
    result["call"] = {k: v for k, v in call.items() if k != "stop"}
    result["observed"] = observed
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="metagente-luna-r1")
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--predecessor", default="")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        result = execute(args.instruction, args.predecessor or None)
        code = 0 if result["status"] == "OBSERVED" else 2 if result["status"] in {"UNMATCHED", "BLOCKED"} else 1
    except Exception:
        result = _base(args.instruction, "ERROR", "UNCAUGHT", "EXCEPTION")
        result["detail"] = traceback.format_exc()[-800:]
        code = 1
    if not result.get("reason"):
        result["reason"] = "MISSING_REASON"
        code = 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state = Path(args.state_dir)
    state.mkdir(parents=True, exist_ok=True)
    with (state / "journal.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.write(json.dumps({"status": result["status"], "stage": result["stage"], "reason": result["reason"]}, ensure_ascii=False) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
