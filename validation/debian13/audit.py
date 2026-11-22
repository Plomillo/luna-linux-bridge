#!/usr/bin/env python3
"""Host-side audit. Does not execute the 36 historical tests or the 803 passed cases."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def git(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    return (proc.stdout or proc.stderr).strip()


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    root = Path(os.environ.get("EVIDENCE", "evidence"))
    repo = Path(os.environ.get("REPO", "."))
    os.chdir(repo)
    head = git(["rev-parse", "HEAD"])
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"])
    status = git(["status", "--porcelain"])
    write(root / "checkpoint.json", {
        "commit": head,
        "branch": branch,
        "status_porcelain": status,
        "reference_commit": "db77c2f27da8060f0362ac8f36cc8860de94c882",
        "matches_reference": head.startswith("db77c2f"),
    })
    cases_path = repo / "reconstruction" / "mra" / "MRA-5O-856-cases.json"
    rows = json.loads(cases_path.read_text()) if cases_path.is_file() else []
    by_status: dict[str, int] = {}
    blocked = []
    historical = []
    for row in rows:
        by_status[row.get("status", "?")] = by_status.get(row.get("status", "?"), 0) + 1
        if row.get("status") == "BLOCKED":
            blocked.append({"n": row.get("n"), "id": row.get("id"), "unlock": row.get("unlock", "")})
        if row.get("status") == "HISTORICAL_PRESERVED":
            historical.append(row.get("id"))
    verify_candidates = list((root / "artifacts").glob("VERIFY.json")) if (root / "artifacts").is_dir() else []
    verify = json.loads(verify_candidates[0].read_text()) if verify_candidates else {}
    mra = verify.get("mra_856") or {}
    write(root / "historical" / "tests-36-audit.json", {
        "reexecuted": 0,
        "sources_inspected": [
            "reconstruction/mra/freeze/MANIFEST.json",
            "reconstruction/mra/MRA-5O-856-cases.json",
            "dist VERIFY.json from actions run 45010622254",
        ],
        "freeze_manifest_present": (repo / "reconstruction" / "mra" / "freeze" / "MANIFEST.json").is_file(),
        "committed_historical_rows": len(historical),
        "committed_historical_ids": historical,
        "aggregate_evidence_sha256": (mra.get("historical_evidence_sha256") or verify.get("mra_oracle", {}).get("evidence_sha256")),
        "individually_verified": 0,
        "missing_individual_evidence": historical,
        "note": "The 36 were not re-executed. The CI artifact stores one aggregate evidence hash, not 36 separate execution records. Individual evidence is therefore not verified.",
    })
    write(root / "cases" / "original-803-audit.json", {
        "reexecuted": 0,
        "verify_pass_functional": mra.get("counts", {}).get("PASS_FUNCTIONAL"),
        "verify_blocked": mra.get("counts", {}).get("BLOCKED"),
        "verify_historical": mra.get("counts", {}).get("HISTORICAL_PRESERVED"),
        "verify_count": mra.get("count"),
        "committed_cases_json_counts": by_status,
        "committed_cases_json_is_stale": by_status.get("PASS_FUNCTIONAL") != 803,
        "individually_verified": 0,
        "note": "Run 45010622254 VERIFY.json records 803 PASS_FUNCTIONAL as an aggregate. It does not ship per-case evidence. Those 803 were not re-executed.",
    })
    search = {
        "looked_for": "a register of exactly 53 original blocked case ids",
        "sources": [
            "reconstruction/mra/MRA-5O-856-cases.json",
            "reconstruction/mra/MRA-5O-144-CLOSURE.json",
            "reconstruction/mra/MRA-5O-856-REPORT.md",
            "VERIFY.json of actions run 45010622254",
            "git history of this checkout",
        ],
        "committed_blocked_count": len(blocked),
        "committed_blocked_ids": [row["n"] for row in blocked],
        "verify_blocked_count": mra.get("counts", {}).get("BLOCKED"),
        "arithmetic_856_minus_803": 53,
        "arithmetic_explanation": "803 PASS_FUNCTIONAL + 17 BLOCKED + 36 HISTORICAL_PRESERVED = 856 on the db77c2f VERIFY. 17+36=53. That is not a third set of 53 blocked ids.",
        "found_register_of_53": False,
        "recovery": "NOT_FOUND_WITH_DOCUMENTED_SEARCH",
    }
    write(root / "cases" / "original-53-recovery.json", search)
    write(root / "cases" / "original-856-register.json", {
        "committed_file": "reconstruction/mra/MRA-5O-856-cases.json",
        "rows": len(rows),
        "counts": by_status,
        "stale_relative_to_verify": True,
    })
    print(json.dumps({"head": head, "blocked_in_commit": len(blocked), "recovery": search["recovery"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
