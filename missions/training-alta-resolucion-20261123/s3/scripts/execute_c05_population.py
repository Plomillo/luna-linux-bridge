#!/usr/bin/env python3
"""Execute source-grounded C05 plans; missing plans remain NOT_RUN.

Plan JSONL record:
{
  "CASE_ID": "MGL5-INF-0001",
  "source_metadata": {
    "source_file": "PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt",
    "line_start": 1, "line_end": 5,
    "file_sha256": "...64 hex...", "excerpt_sha256": "...64 hex...",
    "source_blob": "...Git blob..."
  },
  "source_excerpt": "[MGL5-INF-0001] ...",
  "normal": {"capability_id": "...", "arguments": {}},
  "negative": {
    "capability_id": "...", "arguments": {},
    "control_metadata": {"definition": "...", "expected_behavior": "...", "source": "..."}
  },
  "boundary": {
    "capability_id": "...", "arguments": {},
    "control_metadata": {"definition": "...", "expected_behavior": "...", "source": "..."}
  }
}

The script never infers missing capabilities or invents inputs. It writes a new
ledger and report; it does not mutate historical C05 dossiers or helper ledgers.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from metagente_luna_s4.c05_validator import validate
from metagente_luna_s4.evidence import assemble_case_record
from metagente_luna_s4.independent_validator import independently_validate_case
from metagente_luna_s4.runner import execute_isolated

EXPECTED = [f"MGL5-INF-{number:04d}" for number in range(1, 1001)]


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{number}: expected JSON object")
        rows.append(row)
    return rows


def plan_errors(plan: dict, case_id: str) -> list[str]:
    errors = []
    if plan.get("CASE_ID") != case_id:
        errors.append("case-id-mismatch")
    source = plan.get("source_metadata")
    excerpt = plan.get("source_excerpt")
    required_source_fields = (
        "source_file", "line_start", "line_end", "file_sha256", "excerpt_sha256",
        "source_blob", "operation", "acceptance_criterion", "oracle_requirement",
    )
    if (not isinstance(source, dict) or not isinstance(excerpt, str) or case_id not in excerpt
            or any(not source.get(field) for field in required_source_fields)):
        errors.append("source-provenance-missing")
    else:
        if any(source[field] not in excerpt for field in ("operation", "acceptance_criterion", "oracle_requirement")):
            errors.append("source-operation-criterion-or-oracle-not-bound")
        root = Path(__file__).resolve().parents[4]
        try:
            source_path = (root / source["source_file"]).resolve()
            source_path.relative_to(root)
            source_bytes = source_path.read_bytes()
            lines = source_bytes.splitlines(keepends=True)
            start, end = source["line_start"], source["line_end"]
            exact = b"".join(lines[start - 1:end])
            git_blob = hashlib.sha1(f"blob {len(source_bytes)}\0".encode("ascii") + source_bytes).hexdigest()
            if hashlib.sha256(source_bytes).hexdigest() != source["file_sha256"]:
                errors.append("source-file-sha256-mismatch")
            if git_blob != source["source_blob"]:
                errors.append("source-git-blob-mismatch")
            if start < 1 or end < start or end > len(lines) or exact.decode("utf-8") != excerpt:
                errors.append("source-line-range-mismatch")
            if hashlib.sha256(exact).hexdigest() != source["excerpt_sha256"]:
                errors.append("source-excerpt-sha256-mismatch")
        except (KeyError, OSError, UnicodeError, ValueError, TypeError):
            errors.append("source-file-unavailable-or-invalid")
    for name in ("normal", "negative", "boundary"):
        item = plan.get(name)
        if not isinstance(item, dict) or not isinstance(item.get("capability_id"), str) or not isinstance(item.get("arguments"), dict):
            errors.append(f"{name}-execution-plan-incomplete")
    for name in ("negative", "boundary"):
        item = plan.get(name)
        control = item.get("control_metadata") if isinstance(item, dict) else None
        if not isinstance(control, dict) or not all(
            isinstance(control.get(field), str) and control[field]
            for field in ("definition", "expected_behavior", "source")
        ):
            errors.append(f"{name}-control-definition-incomplete")
    return errors


def execute_plan(plan: dict, case_id: str, evidence_root: Path, timeout_seconds: int) -> dict:
    source_metadata = plan["source_metadata"]
    source_excerpt = plan["source_excerpt"]
    normal = plan["normal"]
    runs = [
        execute_isolated(
            normal["capability_id"], normal["arguments"], case_id,
            evidence_root=str(evidence_root), run_kind="NORMAL",
            source_metadata=source_metadata, source_excerpt=source_excerpt,
            timeout_seconds=timeout_seconds,
        )
        for _ in range(3)
    ]
    for kind in ("negative", "boundary"):
        item = plan[kind]
        runs.append(execute_isolated(
            item["capability_id"], item["arguments"], case_id,
            evidence_root=str(evidence_root), run_kind=kind.upper(),
            control_metadata=item["control_metadata"],
            source_metadata=source_metadata, source_excerpt=source_excerpt,
            timeout_seconds=timeout_seconds,
        ))
    row = assemble_case_record(case_id, runs)
    row["source_metadata"] = source_metadata
    row["independent_validation"] = independently_validate_case(row, evidence_root)
    return row


def write_exclusive(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
        stream.flush()


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        print("Usage: execute_c05_population.py DOSSIERS.jsonl PLANS.jsonl EVIDENCE_ROOT NEW_LEDGER.jsonl NEW_REPORT.json", file=sys.stderr)
        return 2
    dossiers_path, plans_path, evidence_root, ledger_path, report_path = map(Path, argv[1:])
    if not dossiers_path.is_file() or not plans_path.is_file():
        print("dossiers or plans file not found", file=sys.stderr)
        return 2
    dossiers = read_jsonl(dossiers_path)
    plans = read_jsonl(plans_path)
    dossier_ids = [row.get("CASE_ID") or row.get("case_id") for row in dossiers]
    if dossier_ids != EXPECTED:
        print("dossier population must contain exactly INF-0001 through INF-1000 in canonical order", file=sys.stderr)
        return 2
    plan_map = {}
    for plan in plans:
        case_id = plan.get("CASE_ID")
        if case_id in plan_map:
            print(f"duplicate execution plan: {case_id}", file=sys.stderr)
            return 2
        plan_map[case_id] = plan
    unknown = set(plan_map) - set(EXPECTED)
    if unknown:
        print(f"plans contain unknown case IDs: {sorted(unknown)[:10]}", file=sys.stderr)
        return 2

    if ledger_path.exists() or report_path.exists():
        print("ledger/report output already exists; refusing to overwrite historical evidence", file=sys.stderr)
        return 2
    evidence_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for case_id in EXPECTED:
        plan = plan_map.get(case_id)
        if plan is None:
            rows.append({
                "CASE_ID": case_id, "execution_status": "NOT_RUN",
                "contract_status": "NOT_A_PASS", "reason": "NO_SOURCE_GROUNDED_EXECUTION_PLAN",
            })
            continue
        errors = plan_errors(plan, case_id)
        if errors:
            rows.append({
                "CASE_ID": case_id, "execution_status": "NOT_RUN",
                "contract_status": "NOT_A_PASS", "reason": "INVALID_EXECUTION_PLAN",
                "plan_errors": errors,
            })
            continue
        try:
            rows.append(execute_plan(plan, case_id, evidence_root, 60))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            rows.append({
                "CASE_ID": case_id, "execution_status": "INCONCLUSIVE",
                "contract_status": "NOT_A_PASS",
                "reason": f"EXECUTION_OR_EVIDENCE_FAILURE:{type(exc).__name__}:{exc}",
            })

    report = validate(rows, evidence_root=evidence_root)
    ledger_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    report_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    write_exclusive(ledger_path, ledger_text)
    write_exclusive(report_path, report_text)
    print(json.dumps({
        "c05_status": report["c05_status"],
        "authentic_results": report["authentic_results"],
        "not_run": report["not_run"],
        "rejected": len(report["rejected"]),
        "ledger": str(ledger_path),
        "report": str(report_path),
    }, ensure_ascii=False))
    return 0 if report["c05_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
