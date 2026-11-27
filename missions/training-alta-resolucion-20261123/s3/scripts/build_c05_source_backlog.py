#!/usr/bin/env python3
"""Build an append-only source-grounded C05 planning backlog; never invent execution plans."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt"
OUTPUT = ROOT / "missions/training-alta-resolucion-20261123/s3/reports/C05_SOURCE_PLAN_BACKLOG.jsonl"
REPORT = ROOT / "missions/training-alta-resolucion-20261123/s3/reports/C05_SOURCE_PLAN_BACKLOG_SUMMARY.json"
EXPECTED = [f"MGL5-INF-{i:04d}" for i in range(1, 1001)]
PATTERN = re.compile(r"^\\[MGL5-INF-(\\d{4})\\] (.+)$", re.MULTILINE)


def main() -> int:
    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)
    matches = list(PATTERN.finditer(text))
    ids = [f"MGL5-INF-{m.group(1)}" for m in matches]
    if ids != EXPECTED:
        raise SystemExit(f"source corpus mismatch: {len(ids)} records, duplicate/missing/order defect")
    source_sha = hashlib.sha256(raw).hexdigest()
    git_blob = hashlib.sha1(f"blob {len(raw)}\\0".encode("ascii") + raw).hexdigest()
    rows = []
    for index, match in enumerate(matches):
        start = text.count("\\n", 0, match.start()) + 1
        end_offset = matches[index + 1].start() if index + 1 < len(matches) else text.find("PARTE II", match.end())
        if end_offset < 0:
            end_offset = len(text)
        end = text.count("\\n", 0, end_offset) + 1
        excerpt = text[match.start():end_offset].rstrip("\\n")
        case_id = f"MGL5-INF-{match.group(1)}"
        def value(prefix: str) -> str:
            found = next((line.split(":", 1)[1].strip() for line in excerpt.splitlines() if line.startswith(prefix)), "")
            return found
        row = {
            "CASE_ID": case_id,
            "source": {
                "file": SOURCE.name, "line_start": start, "line_end": end,
                "source_sha256": source_sha, "source_blob": git_blob,
                "excerpt_sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
                "excerpt": excerpt,
            },
            "title": match.group(2),
            "operation": value("FUENTE/OPERACIÓN:"),
            "fixture_and_execution": value("FIXTURE+EJECUCIÓN:"),
            "acceptance_criterion": value("PASS:"),
            "oracle_requirement": value("ORÁCULO:"),
            "seed": match.group(1),
            "plan_state": "PLAN_NOT_AUTHORED",
            "normal_plan": None,
            "negative_control_plan": None,
            "boundary_control_plan": None,
            "execution_state": "NOT_RUN",
            "notes": "No capability, argument, fixture, negative, boundary, or outcome is inferred by this backlog generator.",
        }
        rows.append(row)
    if OUTPUT.exists() or REPORT.exists():
        raise SystemExit("refusing overwrite: backlog/report already exists; use a new versioned output path")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True)+"\\n" for row in rows), encoding="utf-8")
    domains = {}
    for row in rows:
        domain = re.search(r"\\bD(\\d{2})\\b", row["title"])
        if domain:
            domains[domain.group(1)] = domains.get(domain.group(1), 0)+1
    summary = {
        "source_sha256": source_sha, "source_blob": git_blob,
        "case_count": len(rows), "unique_ids": len(set(ids)),
        "domain_counts": domains, "all_plans_authored": False,
        "planned": 0, "not_run": len(rows),
        "status": "SOURCE_BOUND_BACKLOG_ONLY_NOT_EXECUTION",
        "plan_fields_null_by_design": True,
    }
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)+"\\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
