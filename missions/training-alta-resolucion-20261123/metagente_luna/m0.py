"""M0 entry point. One instruction in, one observed result out."""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

from metagente_luna import mechanisms
from metagente_luna.parse import Unmatched, parse

IDENTITY = json.loads((Path(__file__).with_name("identity.json")).read_text(encoding="utf-8"))


def execute(instruction: str) -> dict:
    call = parse(instruction)
    tool = getattr(mechanisms, call["tool"])
    observed = tool(**{k: v for k, v in call.items() if k != "tool"})
    return {
        "agent": IDENTITY["AGENT_ID"],
        "version": IDENTITY["AGENT_VERSION"],
        "machinery": "M0",
        "provenance": IDENTITY["PROVENANCE"],
        "instruction": instruction,
        "call": call,
        "observed": observed,
        "status": "OBSERVED",
    }


def remember(state_dir: Path, record: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    journal = state_dir / "journal.jsonl"
    with journal.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="metagente-luna-m0")
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    try:
        result = execute(args.instruction)
        code = 0
    except Unmatched as exc:
        result = {
            "agent": IDENTITY["AGENT_ID"],
            "version": IDENTITY["AGENT_VERSION"],
            "machinery": "M0",
            "instruction": args.instruction,
            "status": "UNMATCHED",
            "reason": str(exc),
        }
        code = 2
    except Exception as exc:
        result = {
            "agent": IDENTITY["AGENT_ID"],
            "version": IDENTITY["AGENT_VERSION"],
            "machinery": "M0",
            "instruction": args.instruction,
            "status": "ERROR",
            "error": type(exc).__name__,
            "detail": traceback.format_exc()[-800:],
        }
        code = 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    remember(Path(args.state_dir), result)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
