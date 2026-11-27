#!/usr/bin/env python3
"""Compile only pre-authored, source-bound INF plans with both controls."""
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
SOURCE_PATH = ROOT / "PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt"
CONTROL_PATH = Path(__file__).resolve().parents[1] / "src" / "metagente_luna_s4" / "controls.py"
CASE_SPECS = D01 + BATCH2 + BATCH3 + BATCH4 + BATCH5
CASE_HEADER = re.compile(r"(?m)^\\[(MGL5-INF-\\d{4})\\].*$")


def _source_record(case_id: str, source: bytes, text: str, lines: list[bytes]) -> tuple[dict, str]:
    match = re.search(rf"(?m)^\\[{re.escape(case_id)}\\].*?(?=^\\[MGL5-INF-|\\Z)", text, re.S)
    if match is None:
        raise ValueError(f"source case missing: {case_id}")
    excerpt = match.group(0)
    start = text[:match.start()].count("\\n") + 1
    end = excerpt.count("\\n") + start - (1 if excerpt.endswith("\\n") else 0)
    exact = b"".join(lines[start - 1:end])
    if exact.decode("utf-8") != excerpt:
        raise ValueError(f"source line range mismatch: {case_id}")
    fields = {}
    for name, pattern in (
        ("operation", r"(?m)^FUENTE/OPERACIÓN:\\s*(.*)$"),
        ("acceptance_criterion", r"(?m)^PASS:\\s*(.*)$"),
        ("oracle_requirement", r"(?m)^ORÁCULO:\\s*(.*)$"),
    ):
        field_match = re.search(pattern, excerpt)
        if field_match is None or not field_match.group(1).strip():
            raise ValueError(f"source field missing: {case_id}:{name}")
        fields[name] = field_match.group(1).strip()
    blob = hashlib.sha1(f"blob {len(source)}\\0".encode("ascii") + source).hexdigest()
    metadata = {
        "source_file": SOURCE_PATH.name,
        "line_start": start,
        "line_end": end,
        "file_sha256": hashlib.sha256(source).hexdigest(),
        "excerpt_sha256": hashlib.sha256(exact).hexdigest(),
        "source_blob": blob,
        **fields,
    }
    return metadata, excerpt


def compile_plans() -> tuple[list[dict], dict]:
    source = SOURCE_PATH.read_bytes()
    text = source.decode("utf-8")
    lines = source.splitlines(keepends=True)
    control_lines = CONTROL_PATH.read_text(encoding="utf-8").splitlines()
    build_controls()
    normal_by_id = {}
    for spec in CASE_SPECS:
        case_id = spec.get("case_id")
        if not isinstance(case_id, str):
            continue
        if case_id in normal_by_id:
            raise ValueError(f"duplicate normal plan: {case_id}")
        normal_by_id[case_id] = spec

    plans = []
    skipped = []
    for case_id, normal in normal_by_id.items():
        controls = CONTROLS.get(case_id, {})
        if set(controls) != {"negative", "boundary"}:
            skipped.append({"case_id": case_id, "reason": "BOTH_CONTROLS_NOT_AUTHORED"})
            continue
        all_specs = [normal, controls["negative"], controls["boundary"]]
        if any(spec.get("capability_id") not in REGISTRY for spec in all_specs):
            skipped.append({"case_id": case_id, "reason": "CAPABILITY_NOT_REGISTERED"})
            continue
        if not isinstance(normal.get("arguments"), dict):
            skipped.append({"case_id": case_id, "reason": "NORMAL_ARGUMENTS_MISSING"})
            continue
        metadata, excerpt = _source_record(case_id, source, text, lines)
        plan = {
            "CASE_ID": case_id,
            "source_metadata": metadata,
            "source_excerpt": excerpt,
            "normal": {
                "capability_id": normal["capability_id"],
                "arguments": normal["arguments"],
                "fixture_provenance": normal.get("fixture_provenance", "PROGRAM_LITERAL"),
            },
        }
        for kind in ("negative", "boundary"):
            control = controls[kind]
            if not isinstance(control.get("arguments"), dict) or not isinstance(control.get("expect"), str):
                raise ValueError(f"incomplete {kind} control: {case_id}")
            catalog_line = next(
                (number for number, line in enumerate(control_lines, start=1)
                 if f'_add("{case_id}", "{kind}",' in line),
                None,
            )
            if catalog_line is None:
                raise ValueError(f"control source line missing: {case_id}:{kind}")
            expect = control["expect"]
            plan[kind] = {
                "capability_id": control["capability_id"],
                "arguments": control["arguments"],
                "control_metadata": {
                    "definition": f"{kind.upper()} control authored in controls.py",
                    "expected_behavior": f"controls.accepts({expect!r}, observed, lifecycle_status) must be true",
                    "source": f"{CONTROL_PATH.relative_to(ROOT)}:{catalog_line}; {SOURCE_PATH.name}:{metadata['line_start']}-{metadata['line_end']}",
                    "expect": expect,
                    "catalog_line": catalog_line,
                },
            }
        plans.append(plan)

    plans.sort(key=lambda item: item["CASE_ID"])
    ids = [item["CASE_ID"] for item in plans]
    if len(ids) != len(set(ids)):
        raise ValueError("compiled plan IDs are not unique")
    report = {
        "status": "SOURCE_BOUND_PARTIAL_PLAN_SET_NOT_CERTIFICATION",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "source_git_blob": hashlib.sha1(f"blob {len(source)}\\0".encode("ascii") + source).hexdigest(),
        "authored_normal_specs": len(normal_by_id),
        "compiled_executable_plans": len(plans),
        "skipped_specs": len(skipped),
        "compiled_case_ids": ids,
        "skipped": skipped,
        "not_in_plan_set": 1000 - len(plans),
        "certification": "NOT_PASSED",
    }
    return plans, report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    plans, report = compile_plans()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() or args.report.exists():
        raise SystemExit("refusing to overwrite existing plan output")
    args.output.write_text(
        "".join(json.dumps(plan, ensure_ascii=False, sort_keys=True) + "\\n" for plan in plans),
        encoding="utf-8",
    )
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(json.dumps({
        "compiled_executable_plans": report["compiled_executable_plans"],
        "skipped_specs": report["skipped_specs"],
        "not_in_plan_set": report["not_in_plan_set"],
        "status": report["status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
