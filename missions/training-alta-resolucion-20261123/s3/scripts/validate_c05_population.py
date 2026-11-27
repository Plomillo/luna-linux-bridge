#!/usr/bin/env python3
"""Validate C05 execution records against persisted evidence artifacts.

Usage:
  python scripts/validate_c05_population.py DOSSIERS.jsonl EVIDENCE_ROOT REPORT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from metagente_luna_s4.c05_validator import validate


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: each JSONL record must be an object")
        rows.append(value)
    return rows


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    dossiers_path, evidence_root, report_path = map(Path, argv[1:])
    if not dossiers_path.is_file():
        print(f"dossier file not found: {dossiers_path}", file=sys.stderr)
        return 2
    if not evidence_root.is_dir():
        print(f"evidence root not found: {evidence_root}", file=sys.stderr)
        return 2
    try:
        rows = read_jsonl(dossiers_path)
        report = validate(rows, evidence_root=evidence_root)
    except (OSError, UnicodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "c05_status": report["c05_status"],
        "rows": report["rows"],
        "authentic_results": report["authentic_results"],
        "not_run": report["not_run"],
        "rejected": len(report["rejected"]),
        "report": str(report_path),
    }, ensure_ascii=False))
    return 0 if report["c05_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
