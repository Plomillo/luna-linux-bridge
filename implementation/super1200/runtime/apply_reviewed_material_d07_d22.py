#!/usr/bin/env python3
"""Re-run reviewed D07–D22 tranche tests. Does not grant certification."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "continuity/REVIEWED_TRANCHES.json"


def main() -> int:
    state = json.loads((ROOT / "continuity/STATE.json").read_text(encoding="utf-8"))
    if state.get("certified") is not False or state.get("global_certification_status") != "NOT_CERTIFIED":
        print("DENY_GLOBAL_CERTIFICATION_FLAG", file=sys.stderr)
        return 2
    if state.get("synthetic_materializer") != "DISABLED":
        print("DENY_SYNTHETIC_MATERIALIZER", file=sys.stderr)
        return 2
    rows = [
        row
        for row in json.loads(MANIFEST.read_text(encoding="utf-8"))["tranches"]
        if row["from"] >= 231
    ]
    if not rows:
        print("DENY_NO_REVIEWED_D07_TRANCHES", file=sys.stderr)
        return 2
    for row in rows:
        test = ROOT / row["test"]
        proc = subprocess.run(
            [sys.executable, "-B", str(test)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=120,
        )
        output = proc.stdout + "\n" + proc.stderr
        if proc.returncode != 0 or "\nOK" not in output:
            print(output[-2000:])
            print(f"SUPER1200_TELEMETRY MATERIAL_TEST_FAIL {row['domain_id']} {row['from']}-{row['to']}")
            return 1
    print(json.dumps({
        "event": "D07_D22_REVIEWED_TESTS_PASS",
        "tranches": len(rows),
        "certification_granted": False,
        "global_certification_status": "NOT_CERTIFIED",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
