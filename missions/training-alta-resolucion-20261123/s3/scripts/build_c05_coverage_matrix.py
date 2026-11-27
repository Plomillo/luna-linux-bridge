#!/usr/bin/env python3
"""Emit a source-hashed, per-case C05 implementation and control coverage matrix."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from metagente_luna_s3.registry import REGISTRY
from metagente_luna_s4.batch2 import CASES as BATCH2
from metagente_luna_s4.batch3 import CASES as BATCH3
from metagente_luna_s4.batch4 import CASES as BATCH4
from metagente_luna_s4.batch5 import CASES as BATCH5
from metagente_luna_s4.controls import CONTROLS, _build as build_controls
from metagente_luna_s4.d01_batch import CASES as D01

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt"
OUTPUT = Path(__file__).resolve().parents[1] / "reports" / "C05_COVERAGE_MATRIX.jsonl"
SUMMARY = Path(__file__).resolve().parents[1] / "reports" / "C05_COVERAGE_MATRIX_SUMMARY.json"


def build() -> tuple[list[dict], dict]:
    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8")
    source_hash = hashlib.sha256(raw).hexdigest()
    source_ids = {
        match.group(1)
        for match in re.finditer(r"(?m)^\[(MGL5-INF-\d{4})\]", text)
    }
    specs = D01 + BATCH2 + BATCH3 + BATCH4 + BATCH5
    by_id: dict[str, dict] = {}
    duplicates: set[str] = set()
    for spec in specs:
        case_id = spec.get("case_id")
        if not isinstance(case_id, str):
            continue
        if case_id in by_id:
            duplicates.add(case_id)
        by_id[case_id] = spec

    build_controls()
    rows = []
    for number in range(1, 1001):
        case_id = f"MGL5-INF-{number:04d}"
        spec = by_id.get(case_id)
        controls = CONTROLS.get(case_id, {})
        reasons = []
        if case_id not in source_ids:
            reasons.append("SOURCE_CASE_MISSING")
        if spec is None:
            reasons.append("NORMAL_EXECUTION_SPEC_MISSING")
        else:
            capability = spec.get("capability_id")
            if capability not in REGISTRY:
                reasons.append("NORMAL_CAPABILITY_UNREGISTERED")
            if not isinstance(spec.get("arguments"), dict):
                reasons.append("NORMAL_ARGUMENTS_NOT_TYPED_OBJECT")
        if "negative" not in controls:
            reasons.append("NEGATIVE_CONTROL_MISSING")
        elif controls["negative"].get("capability_id") not in REGISTRY:
            reasons.append("NEGATIVE_CAPABILITY_UNREGISTERED")
        if "boundary" not in controls:
            reasons.append("BOUNDARY_CONTROL_MISSING")
        elif controls["boundary"].get("capability_id") not in REGISTRY:
            reasons.append("BOUNDARY_CAPABILITY_UNREGISTERED")
        if case_id in duplicates:
            reasons.append("DUPLICATE_NORMAL_SPEC")
        rows.append({
            "CASE_ID": case_id,
            "source_defined": case_id in source_ids,
            "normal_spec_defined": spec is not None,
            "normal_capability": spec.get("capability_id") if spec else None,
            "negative_control_defined": "negative" in controls,
            "boundary_control_defined": "boundary" in controls,
            "ready_for_execution": not reasons,
            "blockers": reasons,
        })

    counts = {
        "source_defined": sum(row["source_defined"] for row in rows),
        "normal_spec_defined": sum(row["normal_spec_defined"] for row in rows),
        "negative_control_defined": sum(row["negative_control_defined"] for row in rows),
        "boundary_control_defined": sum(row["boundary_control_defined"] for row in rows),
        "ready_for_execution": sum(row["ready_for_execution"] for row in rows),
        "blocked": sum(not row["ready_for_execution"] for row in rows),
    }
    blocker_counts: dict[str, int] = {}
    for row in rows:
        for reason in row["blockers"]:
            blocker_counts[reason] = blocker_counts.get(reason, 0) + 1
    summary = {
        "status": "SOURCE_BOUND_COVERAGE_INVENTORY_NOT_EXECUTION",
        "source_file": SOURCE.name,
        "source_sha256": source_hash,
        "expected_cases": 1000,
        "counts": counts,
        "blocker_counts": blocker_counts,
        "certification": "NOT_PASSED",
    }
    return rows, summary


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    rows, summary = build()
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if args.require_complete:
        if summary["counts"]["ready_for_execution"] != 1000:
            print("C05 plan coverage gate failed: all 1,000 cases require a normal plan, registered capability, negative control, and boundary control.", file=__import__("sys").stderr)
            return 1
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    for target in (OUTPUT, SUMMARY):
        if target.exists():
            raise SystemExit(f"refusing to overwrite existing coverage artifact: {target}")
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
