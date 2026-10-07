#!/usr/bin/env python3
"""One-shot elastic planner tick. A user-level timer may call this after review.

No executable remote ingress, no arbitrary scripts, and no privilege operations.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import sys

import elastic_automation as elastic


class Scheduler:
    def __init__(self, automation):
        self.automation = automation
        self.tick_lock = automation.state / "ELASTIC_TICK.lock"

    def select(self):
        """Select earliest UTC-deadline eligible task without touching its state."""
        with self.automation.exclusive() as commits:
            data = self.automation.read(commits)
            active = []
            expired = 0
            gated = 0
            for mid, row in data["missions"].items():
                if row["status"] != "ADMITTED_UNCERTIFIED":
                    gated += 1
                    continue
                req = row["request"]
                if self.automation.clock() >= elastic.deadline(req["deadline_utc"]):
                    expired += 1
                    continue
                if row["next_step"] >= req["max_auto_steps"]:
                    gated += 1
                    continue
                active.append((elastic.deadline(req["deadline_utc"]), mid))
            active.sort()
            return (active[0][1] if active else None,
                    {"eligible": len(active), "expired": expired, "noneligible": gated})

    def tick(self, dry_run=False):
        with self.tick_lock.open("a+b") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return {"status": "BUSY_OTHER_TICK", "executed_steps": 0}
            chosen, counts = self.select()
            if not chosen:
                return {"status": "IDLE_NO_ELIGIBLE_TASK", "executed_steps": 0,
                        "inventory": counts, "certified": False}
            if dry_run:
                return {"status": "DRY_RUN_UNCERTIFIED", "selected": chosen,
                        "executed_steps": 0, "inventory": counts, "certified": False}
            result = self.automation.run_once(chosen)
            return {"status": result["status"], "selected": chosen,
                    "executed_steps": 1 if result["operation"] == "STEP_COMPLETE" else 0,
                    "operation": result["operation"], "inventory": counts,
                    "g23": "NOT_EXECUTED", "g24": "NOT_EXECUTED", "certified": False}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--contract", default=str(Path(__file__).with_name("CONTRACT.v0.json")))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract = json.loads(Path(args.contract).read_text())
        agent = elastic.Automation(args.state_dir, contract)
        result = Scheduler(agent).tick(dry_run=args.dry_run)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if not result["status"].startswith("HOLD") else 3
    except Exception as exc:
        print(json.dumps({"status": "HOLD", "reason": str(exc)[:180]}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
