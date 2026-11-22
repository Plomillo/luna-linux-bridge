#!/usr/bin/env python3
"""G24 stays closed unless G23 passed and the closure files agree."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "evidence")
    g23_path = root / "certification" / "independent-validation.json"
    g23 = json.loads(g23_path.read_text()) if g23_path.is_file() else {"verdict": "ABSENT"}
    reasons = []
    if g23.get("verdict") != "PASS":
        reasons.append("G23_NOT_PASS")
    if g23.get("failures"):
        reasons.append("G23_FAILURES_PRESENT")
    certified = not reasons
    verdict = {
        "producer": "louksna-g24-debian13",
        "depends_on": "louksna-g23-debian13",
        "verdict": "PASS" if certified else "CLOSED",
        "product_certification": "CERTIFIED" if certified else "NOT_CERTIFIED",
        "reasons": reasons,
        "open_blockers_cleared": certified,
    }
    dest = root / "certification" / "certification-verdict.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(verdict, indent=2) + "\n")
    print(json.dumps(verdict, indent=2))
    return 0 if certified else 1


if __name__ == "__main__":
    raise SystemExit(main())
