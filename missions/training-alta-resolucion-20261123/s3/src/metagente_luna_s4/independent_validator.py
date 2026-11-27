"""Independent C05 evidence review; intentionally separate from c05_validator.py."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

VALIDATOR_ID = "LUNA_C05_INDEPENDENT_VALIDATOR"
VALIDATOR_VERSION = "1.0.0"
REQUIRED = {
    "fixture", "environment", "procedure", "control_spec", "stdout", "stderr",
    "observed", "oracle", "metrics", "oracle_source", "producer_source", "source_excerpt",
}


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def evidence_digest(row: dict) -> str:
    entries = []
    for run in (row.get("repetitions") or []) + (row.get("controls") or []):
        if not isinstance(run, dict):
            continue
        for name, artifact in (run.get("artifacts") or {}).items():
            if isinstance(artifact, dict):
                entries.append({
                    "kind": run.get("kind"),
                    "run_id": run.get("run_id"),
                    "name": name,
                    "path": artifact.get("path"),
                    "sha256": artifact.get("sha256"),
                })
    encoded = json.dumps(sorted(entries, key=lambda item: (str(item["run_id"]), item["name"])),
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _digest(encoded)


def _artifact(root: Path, item: dict) -> tuple[bytes | None, str | None]:
    if not isinstance(item, dict):
        return None, "manifest-entry-invalid"
    relative = item.get("path")
    expected = item.get("sha256")
    if not isinstance(relative, str) or not relative or not isinstance(expected, str):
        return None, "manifest-reference-incomplete"
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None, "path-escapes-evidence-root"
    try:
        data = path.read_bytes()
    except OSError:
        return None, "artifact-unreadable"
    if _digest(data) != expected:
        return None, "artifact-sha256-mismatch"
    return data, None


def _json(data: bytes | None) -> dict | None:
    if data is None:
        return None
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def independently_validate_case(row: dict, evidence_root: str | Path) -> dict:
    """Recompute evidence integrity without invoking the primary C05 validator."""
    root = Path(evidence_root).resolve()
    case_id = row.get("CASE_ID") or row.get("case_id")
    normal = row.get("repetitions")
    controls = row.get("controls")
    findings: list[str] = []
    if not isinstance(normal, list) or len(normal) != 3:
        findings.append("normal-repetition-count-not-three")
        normal = normal if isinstance(normal, list) else []
    if not isinstance(controls, list) or len(controls) != 2:
        findings.append("negative-boundary-control-count-not-two")
        controls = controls if isinstance(controls, list) else []
    runs = normal + controls
    if [run.get("kind") for run in normal if isinstance(run, dict)] != ["NORMAL"] * len(normal):
        findings.append("normal-run-kind-mismatch")
    if {run.get("kind") for run in controls if isinstance(run, dict)} != {"NEGATIVE", "BOUNDARY"}:
        findings.append("control-kind-mismatch")

    seen_runs: set[str] = set()
    inputs: dict[str, list[str]] = {"NORMAL": [], "NEGATIVE": [], "BOUNDARY": []}
    checked_artifacts = 0
    for run in runs:
        if not isinstance(run, dict):
            findings.append("run-record-invalid")
            continue
        run_id = run.get("run_id")
        kind = run.get("kind")
        if not isinstance(run_id, str) or not run_id or run_id in seen_runs:
            findings.append("run-id-missing-or-duplicated")
        else:
            seen_runs.add(run_id)
        if run.get("case_id") != case_id:
            findings.append("run-case-identity-mismatch")
        if kind not in inputs:
            findings.append("run-kind-invalid")
        if run.get("execution_status") not in {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"}:
            findings.append("run-outcome-invalid")
        if run.get("clean_state") is not True:
            findings.append("clean-process-state-not-proven")
        if not isinstance(run.get("exit_code"), int) or isinstance(run.get("exit_code"), bool):
            findings.append("exit-code-missing")
        artifacts = run.get("artifacts")
        if not isinstance(artifacts, dict) or REQUIRED - set(artifacts):
            findings.append("required-artifacts-missing")
            continue
        loaded: dict[str, bytes] = {}
        for name, reference in artifacts.items():
            data, error = _artifact(root, reference)
            if error:
                findings.append(f"{name}:{error}")
            elif data is not None:
                loaded[name] = data
                checked_artifacts += 1

        fixture = _json(loaded.get("fixture"))
        oracle = _json(loaded.get("oracle"))
        environment = _json(loaded.get("environment"))
        procedure = _json(loaded.get("procedure"))
        control_spec = _json(loaded.get("control_spec"))
        observed = _json(loaded.get("observed"))
        metrics = _json(loaded.get("metrics"))
        if not fixture or fixture.get("case_id") != case_id or fixture.get("run_id") != run_id or fixture.get("run_kind") != kind or "input" not in fixture:
            findings.append("fixture-identity-or-input-invalid")
        elif kind in inputs:
            inputs[kind].append(_digest(json.dumps(fixture["input"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))
        source_metadata = fixture.get("source") if isinstance(fixture, dict) else None
        source_excerpt = loaded.get("source_excerpt")
        source_valid = False
        if (isinstance(source_metadata, dict)
                and isinstance(source_metadata.get("source_file"), str)
                and isinstance(source_metadata.get("line_start"), int)
                and isinstance(source_metadata.get("line_end"), int)
                and source_excerpt is not None):
            repository_root = Path(__file__).resolve().parents[5]
            source_path = (repository_root / source_metadata["source_file"]).resolve()
            try:
                source_path.relative_to(repository_root)
                source_bytes = source_path.read_bytes()
                lines = source_bytes.splitlines(keepends=True)
                line_start, line_end = source_metadata["line_start"], source_metadata["line_end"]
                excerpt_bytes = b"".join(lines[line_start - 1:line_end])
                git_blob = hashlib.sha1(f"blob {len(source_bytes)}\\0".encode("ascii") + source_bytes).hexdigest()
                source_valid = (
                    line_start >= 1 and line_end >= line_start and line_end <= len(lines)
                    and _digest(source_bytes) == source_metadata.get("file_sha256")
                    and git_blob == source_metadata.get("source_blob")
                    and excerpt_bytes == source_excerpt
                    and _digest(source_excerpt) == source_metadata.get("excerpt_sha256")
                    and case_id.encode("utf-8") in source_excerpt
                )
            except (OSError, UnicodeError, ValueError, TypeError):
                source_valid = False
        if not source_valid:
            findings.append("source-line-provenance-invalid")
        if not oracle or oracle.get("case_id") != case_id or oracle.get("run_id") != run_id:
            findings.append("oracle-identity-invalid")
        else:
            oracle_source = loaded.get("oracle_source")
            producer_source = loaded.get("producer_source")
            if oracle.get("independent") is not True or oracle.get("producer_used_as_oracle") is True:
                findings.append("oracle-not-independent")
            if not oracle.get("oracle_module") or oracle.get("oracle_module") == oracle.get("producer_module"):
                findings.append("oracle-module-not-distinct")
            if oracle_source is None or producer_source is None:
                findings.append("source-artifacts-missing")
            else:
                if _digest(oracle_source) != oracle.get("oracle_source_sha256"):
                    findings.append("oracle-source-hash-invalid")
                if _digest(producer_source) != oracle.get("producer_source_sha256"):
                    findings.append("producer-source-hash-invalid")
                if _digest(oracle_source) == _digest(producer_source):
                    findings.append("oracle-source-equals-producer")
            outcome = run.get("execution_status")
            if outcome == "PASS" and (run.get("exit_code") != 0 or oracle.get("result") != "PASS"):
                findings.append("pass-not-supported-by-oracle")
            if outcome == "FAIL" and oracle.get("result") != "FAIL":
                findings.append("fail-not-supported-by-oracle")
            if outcome in {"BLOCKED", "INCONCLUSIVE"} and oracle.get("result") != "INCONCLUSIVE":
                findings.append("nonterminal-oracle-mismatch")
        if not environment or environment.get("case_id") != case_id or environment.get("run_id") != run_id:
            findings.append("environment-identity-invalid")
        else:
            isolation = environment.get("isolation")
            if (not isinstance(isolation, dict) or isolation.get("mode") != "FRESH_PROCESS_TEMPORARY_WORKSPACE"
                    or isolation.get("process_isolated") is not True or isolation.get("workspace_ephemeral") is not True
                    or isolation.get("cwd_isolated") is not True or isolation.get("home_isolated") is not True
                    or isolation.get("tmp_isolated") is not True or isolation.get("sandbox") is not False):
                findings.append("process-isolation-evidence-invalid")
        if not procedure or procedure.get("case_id") != case_id or procedure.get("run_id") != run_id:
            findings.append("procedure-identity-invalid")
        if not control_spec or control_spec.get("case_id") != case_id or control_spec.get("run_id") != run_id or control_spec.get("run_kind") != kind:
            findings.append("control-spec-identity-invalid")
        elif kind in {"NEGATIVE", "BOUNDARY"} and control_spec.get("control") != (fixture or {}).get("control"):
            findings.append("control-spec-fixture-mismatch")
        if not observed or observed.get("case_id") != case_id or observed.get("run_id") != run_id:
            findings.append("observed-identity-invalid")
        if not metrics or metrics.get("case_id") != case_id or metrics.get("run_id") != run_id:
            findings.append("metrics-identity-invalid")

    if len(inputs["NORMAL"]) != 3 or len(set(inputs["NORMAL"])) != 1:
        findings.append("normal-inputs-not-identical")
    if (len(inputs["NEGATIVE"]) != 1 or len(inputs["BOUNDARY"]) != 1
            or not inputs["NORMAL"] or inputs["NEGATIVE"][0] in inputs["NORMAL"]
            or inputs["BOUNDARY"][0] in inputs["NORMAL"] or inputs["NEGATIVE"] == inputs["BOUNDARY"]):
        findings.append("control-inputs-not-distinct")
    normal_outcomes = [run.get("execution_status") for run in normal if isinstance(run, dict)]
    if len(set(normal_outcomes)) > 1:
        findings.append("normal-outcomes-not-stable")
    if row.get("execution_status") != (normal_outcomes[0] if normal_outcomes else None):
        findings.append("row-outcome-does-not-match-normal-runs")

    status = "PASS" if not findings and len(runs) == 5 else "FAIL"
    return {
        "validator_id": VALIDATOR_ID,
        "validator_version": VALIDATOR_VERSION,
        "status": status,
        "case_id": case_id,
        "evidence_digest": evidence_digest(row),
        "checked_run_count": len(runs),
        "checked_artifact_count": checked_artifacts,
        "method": "INDEPENDENT_RECOMPUTATION",
        "findings": sorted(set(findings)),
    }
