#!/usr/bin/env python3
"""Execute source-grounded C05 plans; incomplete plans remain explicit NOT_RUN blockers.

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

The script never infers missing capabilities or invents inputs. It does not
launch Docker containers for cases that have no executable plan. Those cases
are written to a source-bound NOT_RUN blocker inventory and never counted as
executions. It writes new evidence artifacts; it does not mutate historical
C05 dossiers or helper ledgers.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from metagente_luna_s4.c05_validator import validate
from metagente_luna_s4.controls import accepts as control_accepts
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
    string_source_fields = (
        "source_file", "file_sha256", "excerpt_sha256", "source_blob",
        "operation", "acceptance_criterion", "oracle_requirement",
    )
    valid_source_shape = (
        isinstance(source, dict)
        and all(isinstance(source.get(field), str) and source[field] for field in string_source_fields)
        and isinstance(source.get("line_start"), int) and not isinstance(source.get("line_start"), bool)
        and isinstance(source.get("line_end"), int) and not isinstance(source.get("line_end"), bool)
        and isinstance(excerpt, str) and case_id in excerpt
    )
    if not valid_source_shape:
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
            for field in ("definition", "expected_behavior", "source", "expect")
        ):
            errors.append(f"{name}-control-definition-incomplete")
    return errors


def evaluate_contract(plan: dict, runs: list[dict]) -> dict:
    """Adjudicate three normal repetitions and the authored negative/boundary contracts."""
    if len(runs) != 5:
        return {
            "normal_repetitions_pass": False,
            "normal_repetition_checks": [],
            "controls_pass": False,
            "control_checks": [],
            "adjudicator": "SOURCE_BOUND_PLAN_AND_REGISTERED_CONTROL_EXPECTATIONS",
        }
    normal_checks = [
        run.get("execution_status") == "PASS"
        and run.get("lifecycle_status") == "EXECUTED"
        and isinstance(run.get("oracle_result"), dict)
        and run["oracle_result"].get("ok") is True
        for run in runs[:3]
    ]
    control_checks = []
    for kind, run in zip(("negative", "boundary"), runs[3:], strict=True):
        expected = plan[kind]["control_metadata"]["expect"]
        try:
            accepted = control_accepts(
                expected, run.get("observed"), run.get("lifecycle_status"),
            )
        except (KeyError, TypeError, ValueError):
            accepted = False
        control_checks.append({
            "kind": kind.upper(),
            "expect": expected,
            "lifecycle_status": run.get("lifecycle_status"),
            "accepted": accepted,
        })
    return {
        "normal_repetitions_pass": all(normal_checks),
        "normal_repetition_checks": normal_checks,
        "controls_pass": all(item["accepted"] for item in control_checks),
        "control_checks": control_checks,
        "adjudicator": "SOURCE_BOUND_PLAN_AND_REGISTERED_CONTROL_EXPECTATIONS",
    }


def execute_plan(plan: dict, case_id: str, evidence_root: Path, timeout_seconds: int, sandbox_image: str) -> dict:
    source_metadata = plan["source_metadata"]
    source_excerpt = plan["source_excerpt"]
    normal = plan["normal"]
    runs = [
        execute_isolated(
            normal["capability_id"], normal["arguments"], case_id,
            evidence_root=str(evidence_root), run_kind="NORMAL",
            source_metadata=source_metadata, source_excerpt=source_excerpt,
            timeout_seconds=timeout_seconds, sandbox_image=sandbox_image,
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
            timeout_seconds=timeout_seconds, sandbox_image=sandbox_image,
        ))
    row = assemble_case_record(case_id, runs)
    row["source_metadata"] = source_metadata

    row["contract_evaluation"] = evaluate_contract(plan, runs)
    row["independent_validation"] = independently_validate_case(row, evidence_root)
    contract_pass = (
        row["execution_status"] == "PASS"
        and row["contract_evaluation"]["normal_repetitions_pass"]
        and row["contract_evaluation"]["controls_pass"]
        and row["independent_validation"].get("status") == "PASS"
    )
    row["contract_status"] = "PASS" if contract_pass else "NOT_A_PASS"
    return row


def execute_valid_plans(
    plan_map: dict[str, dict],
    valid_case_ids: set[str],
    evidence_root: Path,
    sandbox_image: str,
    *,
    max_workers: int = 4,
) -> dict[str, dict]:
    """Execute independent case plans concurrently with bounded Docker pressure."""
    items = [
        (case_id, plan_map[case_id])
        for case_id in EXPECTED
        if case_id in valid_case_ids
    ]
    if not items:
        return {}

    def execute_one(item: tuple[str, dict]) -> tuple[str, dict]:
        case_id, plan = item
        try:
            return case_id, execute_plan(plan, case_id, evidence_root, 60, sandbox_image)
        except Exception as exc:  # noqa: BLE001 - preserve each failed case independently
            return case_id, {
                "CASE_ID": case_id,
                "execution_status": "INCONCLUSIVE",
                "contract_status": "NOT_A_PASS",
                "reason": f"EXECUTION_OR_EVIDENCE_FAILURE:{type(exc).__name__}:{exc}",
            }

    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as executor:
        return dict(executor.map(execute_one, items))


def source_record(case_id: str) -> tuple[dict, str]:
    root = Path(__file__).resolve().parents[4]
    source_path = root / "PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt"
    raw = source_path.read_bytes()
    text = raw.decode("utf-8")
    lines = raw.splitlines(keepends=True)
    match = re.search(
        rf"(?m)^\[{re.escape(case_id)}\].*?(?=^\[MGL5-(?:INF|TEO)-|\Z)",
        text,
        re.S,
    )
    if match is None:
        raise ValueError(f"source case missing: {case_id}")
    excerpt = match.group(0)
    start = text[:match.start()].count("\n") + 1
    end = start + excerpt.count("\n") - (1 if excerpt.endswith("\n") else 0)
    exact = b"".join(lines[start - 1:end])
    if exact.decode("utf-8") != excerpt:
        raise ValueError(f"source line range mismatch: {case_id}")
    fields = {}
    for name, pattern in (
        ("operation", r"(?m)^FUENTE/OPERACIÓN:\s*(.*)$"),
        ("acceptance_criterion", r"(?m)^PASS:\s*(.*)$"),
        ("oracle_requirement", r"(?m)^ORÁCULO:\s*(.*)$"),
    ):
        found = re.search(pattern, excerpt)
        if found is None or not found.group(1).strip():
            raise ValueError(f"source field missing: {case_id}:{name}")
        fields[name] = found.group(1).strip()
    return ({
        "source_file": source_path.name,
        "line_start": start,
        "line_end": end,
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "excerpt_sha256": hashlib.sha256(exact).hexdigest(),
        "source_blob": hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest(),
        **fields,
    }, excerpt)


def evidence_inventory_complete(report: dict, executable_case_ids: set[str]) -> bool:
    """Require authentic evidence for every executable plan and explicit NOT_RUN for the rest."""
    expected = report.get("expected")
    rows = report.get("rows")
    not_run = report.get("not_run")
    rejected = report.get("rejected")
    authentic = report.get("authentic_results")
    if not all(isinstance(value, int) and not isinstance(value, bool)
               for value in (expected, rows, not_run, authentic)):
        return False
    if (expected != 1000 or rows != 1000 or not isinstance(executable_case_ids, set)
            or len(executable_case_ids) != authentic or not executable_case_ids.issubset(set(EXPECTED))
            or not_run != 1000 - len(executable_case_ids)):
        return False
    if not isinstance(rejected, list) or len(rejected) != not_run:
        return False
    if not all(isinstance(item, dict) for item in rejected):
        return False
    rejected_ids = [item.get("case_id") for item in rejected]
    expected_ids = set(EXPECTED)
    return (
        len(set(rejected_ids)) == not_run
        and set(rejected_ids) == expected_ids - executable_case_ids
        and all(item.get("reasons") == ["case-not-executed"] for item in rejected)
    )


def write_exclusive(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
        stream.flush()


def main(argv: list[str]) -> int:
    if len(argv) != 7:
        print("Usage: execute_c05_population.py DOSSIERS.jsonl PLANS.jsonl EVIDENCE_ROOT NEW_LEDGER.jsonl NEW_REPORT.json SANDBOX_IMAGE_ID", file=sys.stderr)
        return 2
    dossiers_path, plans_path, evidence_root, ledger_path, report_path = map(Path, argv[1:6])
    sandbox_image = argv[6]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", sandbox_image):
        print("sandbox image must be an immutable sha256:<64 lowercase hex> Docker image ID", file=sys.stderr)
        return 2
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

    blocker_path = ledger_path.with_name("C05_POPULATION_BLOCKERS.jsonl")
    existing_outputs = [path for path in (ledger_path, report_path, blocker_path) if path.exists()]
    if existing_outputs:
        print(
            "output already exists; refusing to overwrite historical evidence: "
            + ", ".join(str(path) for path in existing_outputs),
            file=sys.stderr,
        )
        return 2
    evidence_root.mkdir(parents=True, exist_ok=True)
    coverage_path = Path("reports/C05_COVERAGE_MATRIX.jsonl")
    coverage_map = {}
    if coverage_path.is_file():
        coverage_map = {
            row["CASE_ID"]: row
            for row in read_jsonl(coverage_path)
            if isinstance(row.get("CASE_ID"), str)
        }

    valid_executable_ids = {
        case_id for case_id, plan in plan_map.items()
        if not plan_errors(plan, case_id)
    }
    execution_results = execute_valid_plans(
        plan_map, valid_executable_ids, evidence_root, sandbox_image, max_workers=4,
    )
    rows = []
    blocker_inventory = []
    for case_id in EXPECTED:
        plan = plan_map.get(case_id)
        errors = plan_errors(plan, case_id) if plan is not None else ["NO_COMPLETE_SOURCE_GROUNDED_PLAN"]
        if plan is None or errors:
            coverage = coverage_map.get(case_id, {})
            reasons = coverage.get("blockers", [])
            if not reasons:
                reasons = errors
            metadata, excerpt = source_record(case_id)
            blocker_inventory.append({
                "CASE_ID": case_id,
                "status": "NOT_RUN",
                "operation_invoked": False,
                "blockers": reasons,
                "source_metadata": metadata,
                "source_excerpt": excerpt,
                "certification_effect": "BLOCKS_C05",
            })
            # Do not launch five Docker containers merely to prove that no
            # executable plan exists. NOT_RUN is explicit and never counted
            # as execution; the source-bound blocker is retained separately.
            rows.append({
                "CASE_ID": case_id,
                "execution_status": "NOT_RUN",
                "contract_status": "NOT_A_PASS",
                "reason": "NO_COMPLETE_SOURCE_GROUNDED_EXECUTION_PLAN",
            })
            continue
        rows.append(execution_results[case_id])

    report = validate(rows, evidence_root=evidence_root)
    ledger_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    report_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    blocker_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in blocker_inventory)
    write_exclusive(ledger_path, ledger_text)
    write_exclusive(report_path, report_text)
    write_exclusive(blocker_path, blocker_text)
    execution_failures = [
        {"case_id": row["CASE_ID"], "status": row["execution_status"], "reason": row.get("reason")}
        for row in rows
        if row["execution_status"] in {"INCONCLUSIVE", "FAIL", "BLOCKED"}
    ]
    print(json.dumps({
        "c05_status": report["c05_status"],
        "sandbox_image_id": sandbox_image,
        "compiled_executable_plans": len(valid_executable_ids),
        "authentic_results": report["authentic_results"],
        "not_run": report["not_run"],
        "rejected": len(report["rejected"]),
        "execution_failures": execution_failures,
        "validation_rejections": len(report["rejected"]),
        "validation_rejection_reasons": {
            reason: sum(reason in item.get("reasons", []) for item in report["rejected"])
            for reason in sorted({
                reason
                for item in report["rejected"]
                for reason in item.get("reasons", [])
            })
        },
        "rejected_case_details": report["rejected"],
        "rejected_evidence_details": [
            {
                "case_id": row["CASE_ID"],
                "execution_status": row.get("execution_status"),
                "contract_status": row.get("contract_status"),
                "contract_evaluation": row.get("contract_evaluation"),
                "independent_validation": row.get("independent_validation"),
                "control_evidence": [
                    {
                        "kind": run.get("kind"),
                        "execution_status": run.get("execution_status"),
                        "fixture": json.loads(
                            (evidence_root / run["artifacts"]["fixture"]["path"]).read_text(encoding="utf-8")
                        ),
                        "observed": json.loads(
                            (evidence_root / run["artifacts"]["observed"]["path"]).read_text(encoding="utf-8")
                        ),
                        "oracle": json.loads(
                            (evidence_root / run["artifacts"]["oracle"]["path"]).read_text(encoding="utf-8")
                        ),
                    }
                    for run in row.get("controls", [])
                ],
                "reason": row.get("reason"),
            }
            for row in rows
            if row.get("CASE_ID") in {
                item.get("case_id") for item in report["rejected"]
            } and row.get("execution_status") != "NOT_RUN"
        ],
        "ledger": str(ledger_path),
        "report": str(report_path),
        "blocker_inventory": str(blocker_path),
        "blocked_cases": len(blocker_inventory),
    }, ensure_ascii=False))
    # Exit successfully only when every authored executable plan produced
    # authentic evidence and the remaining cases are explicit NOT_RUN blockers.
    # This completes evidence collection, not C05.
    return 0 if evidence_inventory_complete(report, valid_executable_ids) and len(blocker_inventory) == 1000 - len(valid_executable_ids) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
