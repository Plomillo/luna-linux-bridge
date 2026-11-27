"""Fail-closed C05 evidence validation.

A dossier is an execution only when its persisted evidence artifacts can be
read from the supplied evidence root and their digests are recomputed from
bytes. Inline self-hashed payloads are deliberately not accepted.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

EXPECTED = [f"MGL5-INF-{number:04d}" for number in range(1, 1001)]
EXECUTION_OUTCOMES = {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"}
REQUIRED_ARTIFACTS = {
    "fixture", "environment", "procedure", "stdout", "stderr",
    "observed", "oracle", "metrics",
}
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


def _sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except (OSError, IsADirectoryError):
        return None


def _safe_artifact(root: Path, item: dict) -> tuple[Path | None, str | None]:
    if not isinstance(item, dict):
        return None, "artifact-entry-invalid"
    relative = item.get("path")
    expected = item.get("sha256")
    if not isinstance(relative, str) or not relative or not isinstance(expected, str):
        return None, "artifact-reference-incomplete"
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        return None, "artifact-digest-invalid"
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None, "artifact-path-escapes-root"
    actual = _sha256(candidate)
    if actual is None:
        return None, "artifact-missing-or-unreadable"
    if actual != expected:
        return None, "artifact-digest-mismatch"
    return candidate, None


def _load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def contradictions(row: dict) -> list[str]:
    found: list[str] = []
    status = row.get("contract_status") or row.get("contractual_status")
    execution = row.get("execution_status")
    basis = row.get("basis") or row.get("promotion_basis")
    if status == "PASS" and basis == "CRITERION_MET":
        found.append("criterion-met-promoted-to-pass")
    if status == "PASS" and execution == "NOT_RUN":
        found.append("not-run-promoted-to-pass")
    if status == "PASS" and execution not in EXECUTION_OUTCOMES:
        found.append("inflated-state")
    if execution == "FAIL" and status == "PASS":
        found.append("fail-promoted-to-contract-pass")
    if execution in {"BLOCKED", "INCONCLUSIVE", "NOT_RUN"} and status == "PASS":
        found.append("non-success-promoted-to-contract-pass")
    if status == "PASS" and row.get("oracle_mode") in {"same-implementation", "self", "producer"}:
        found.append("circular-oracle")
    if row.get("human_reviewer") and not row.get("human_review_evidence"):
        found.append("reviewer-without-evidence")
    if row.get("repetitions_copied") is True:
        found.append("copied-repetition")
    if row.get("evidence_missing") is True:
        found.append("missing-evidence")
    if row.get("execution_status") == "NOT_RUN" and (
        row.get("individual_investigation") is True or row.get("counted_as_execution") is True
    ):
        found.append("investigation-is-not-execution")
    return found


def _validate_repetition(rep: dict, evidence_root: Path, case_id: str) -> list[str]:
    errors: list[str] = []
    run_id = rep.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        errors.append("run-id-invalid")
    if rep.get("case_id") != case_id:
        errors.append("run-case-mismatch")
    if rep.get("clean_state") is not True:
        errors.append("clean-state-not-proven")
    if rep.get("execution_status") not in EXECUTION_OUTCOMES:
        errors.append("execution-outcome-invalid")
    if not isinstance(rep.get("exit_code"), int) or isinstance(rep.get("exit_code"), bool):
        errors.append("exit-code-missing")
    if not isinstance(rep.get("agent_version"), str) or not rep["agent_version"]:
        errors.append("agent-version-missing")
    if not isinstance(rep.get("executor_version"), str) or not rep["executor_version"]:
        errors.append("executor-version-missing")
    if not isinstance(rep.get("machinery"), str) or not rep["machinery"]:
        errors.append("machinery-missing")

    artifacts = rep.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifact-manifest-missing")
        return errors
    missing = REQUIRED_ARTIFACTS - set(artifacts)
    if missing:
        errors.extend(f"artifact-{name}-missing" for name in sorted(missing))
    loaded: dict[str, Path] = {}
    for name, item in artifacts.items():
        path, error = _safe_artifact(evidence_root, item)
        if error:
            errors.append(f"{name}:{error}")
        elif path is not None:
            loaded[name] = path

    oracle = _load_json(loaded["oracle"]) if "oracle" in loaded else None
    if not isinstance(oracle, dict):
        errors.append("oracle-artifact-invalid")
    else:
        if oracle.get("independent") is not True:
            errors.append("oracle-not-independent")
        if oracle.get("producer_used_as_oracle") is True:
            errors.append("oracle-circular")
        if oracle.get("case_id") != case_id or oracle.get("run_id") != run_id:
            errors.append("oracle-provenance-mismatch")

    observed = _load_json(loaded["observed"]) if "observed" in loaded else None
    if not isinstance(observed, dict):
        errors.append("observed-artifact-invalid")
    elif observed.get("case_id") != case_id or observed.get("run_id") != run_id:
        errors.append("observed-provenance-mismatch")

    fixture = _load_json(loaded["fixture"]) if "fixture" in loaded else None
    if not isinstance(fixture, dict) or fixture.get("case_id") != case_id:
        errors.append("fixture-provenance-invalid")

    environment = _load_json(loaded["environment"]) if "environment" in loaded else None
    if not isinstance(environment, dict) or not environment.get("environment_id"):
        errors.append("environment-artifact-invalid")

    procedure = _load_json(loaded["procedure"]) if "procedure" in loaded else None
    if not isinstance(procedure, dict) or procedure.get("case_id") != case_id:
        errors.append("procedure-artifact-invalid")

    metrics = _load_json(loaded["metrics"]) if "metrics" in loaded else None
    if not isinstance(metrics, dict) or metrics.get("case_id") != case_id:
        errors.append("metrics-artifact-invalid")

    if rep.get("execution_status") == "PASS":
        if rep.get("exit_code") != 0:
            errors.append("pass-with-nonzero-exit")
        if not isinstance(oracle, dict) or oracle.get("result") != "PASS":
            errors.append("pass-without-independent-oracle-pass")
    return errors


def _validate_row(row: dict, evidence_root: Path | None) -> list[str]:
    errors = contradictions(row)
    if evidence_root is None:
        errors.append("evidence-root-not-supplied")
        return errors
    if row.get("execution_status") not in EXECUTION_OUTCOMES:
        errors.append("case-not-executed")
        return errors
    case_id = row.get("CASE_ID") or row.get("case_id")
    repetitions = row.get("repetitions")
    if not isinstance(repetitions, list) or len(repetitions) != 3:
        errors.append("exactly-three-repetitions-required")
        return errors
    run_ids: list[str] = []
    outcomes: list[str] = []
    for rep in repetitions:
        if not isinstance(rep, dict):
            errors.append("repetition-entry-invalid")
            continue
        errors.extend(_validate_repetition(rep, evidence_root, case_id))
        if isinstance(rep.get("run_id"), str):
            run_ids.append(rep["run_id"])
        if isinstance(rep.get("execution_status"), str):
            outcomes.append(rep["execution_status"])
    if len(run_ids) != len(set(run_ids)):
        errors.append("duplicate-run-id-within-case")
    if len(set(outcomes)) > 1:
        errors.append("repetition-outcomes-disagree")
    required_kinds = {"NORMAL", "NEGATIVE", "BOUNDARY"}
    kinds = {rep.get("kind") for rep in repetitions if isinstance(rep, dict)}
    if kinds != required_kinds:
        errors.append("normal-negative-boundary-runs-required")
    if row.get("execution_status") != (outcomes[0] if outcomes else None):
        errors.append("case-outcome-does-not-match-repetitions")
    if row.get("contract_status") == "PASS" and row.get("execution_status") != "PASS":
        errors.append("contract-pass-with-nonpass-execution")
    independent = row.get("independent_validation")
    if row.get("contract_status") == "PASS" and (not isinstance(independent, dict) or independent.get("passed") is not True):
        errors.append("contract-pass-without-independent-validation")
    return errors


def validate(rows: list[dict], evidence_root: str | Path | None = None) -> dict:
    """Validate the exact INF population against persisted, byte-verified evidence."""
    identifiers = [row.get("CASE_ID") or row.get("case_id") for row in rows]
    problems = []
    if identifiers != EXPECTED:
        id_set = set(identifiers)
        problems.append({
            "missing": len([case_id for case_id in EXPECTED if case_id not in id_set]),
            "unknown": len([case_id for case_id in identifiers if case_id not in set(EXPECTED)]),
            "duplicates": len(identifiers) - len(id_set),
            "order_mismatch": len(identifiers) == len(EXPECTED) and identifiers != EXPECTED,
        })
    root = Path(evidence_root).resolve() if evidence_root is not None else None
    rejected = []
    run_owner: dict[str, str] = {}
    authentic = 0
    not_run = 0
    contractual_pass = 0
    for row in rows:
        case_id = row.get("CASE_ID") or row.get("case_id")
        if row.get("execution_status") == "NOT_RUN":
            not_run += 1
        if row.get("contract_status") == "PASS":
            contractual_pass += 1
        errors = _validate_row(row, root)
        repetitions = row.get("repetitions")
        if isinstance(repetitions, list):
            for rep in repetitions:
                if not isinstance(rep, dict):
                    continue
                run_id = rep.get("run_id")
                if isinstance(run_id, str):
                    owner = run_owner.setdefault(run_id, case_id)
                    if owner != case_id:
                        errors.append("run-id-reused-across-cases")
        if errors:
            rejected.append({"case_id": case_id, "reasons": sorted(set(errors))})
        else:
            authentic += 1
    passed = not problems and not rejected and authentic == 1000 and not_run == 0
    return {
        "c05_passed": passed,
        "c05_status": "PASS" if passed else "NOT_PASSED",
        "expected": 1000,
        "rows": len(rows),
        "not_run": not_run,
        "not_run_counts_as_execution": False,
        "authentic_results": authentic,
        "contractual_pass": contractual_pass,
        "rejected": rejected,
        "structure_problems": problems,
        "evidence_root_supplied": root is not None,
        "human_review_required": False,
        "reason": "C05 requires 1,000 individually executed dossiers with persisted, byte-verified evidence; investigation and inline hashes are not execution evidence",
    }
