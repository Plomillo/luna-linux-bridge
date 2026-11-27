import hashlib
import json

from metagente_luna_s4.c05_validator import _validate_row, contradictions, validate
from metagente_luna_s4.independent_validator import independently_validate_case
from metagente_luna_s4.reconcile import amendments, intersection, manifest


def _population(status: str, **extra) -> list[dict]:
    rows = []
    for number in range(1, 1001):
        row = {"CASE_ID": f"MGL5-INF-{number:04d}", "execution_status": status, "contract_status": status}
        row.update(extra)
        rows.append(row)
    return rows


def _write_artifact(root, relative, payload):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    else:
        path.write_text(payload, encoding="utf-8")
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _valid_row_with_artifacts(tmp_path):
    case_id = "MGL5-INF-0001"
    repetitions = []
    controls = []
    run_specs = [
        ("NORMAL", {"sample": "normal"}, None),
        ("NORMAL", {"sample": "normal"}, None),
        ("NORMAL", {"sample": "normal"}, None),
        ("NEGATIVE", {"sample": "negative"}, {"definition": "negative input", "expected_behavior": "reject invalid input", "source": "test-spec"}),
        ("BOUNDARY", {"sample": "boundary"}, {"definition": "boundary input", "expected_behavior": "accept boundary", "source": "test-spec"}),
    ]
    for index, (kind, input_value, control) in enumerate(run_specs, start=1):
        run_id = f"run-0001-{index:04d}"
        oracle_source = _write_artifact(tmp_path, f"{run_id}/oracle_source.py", "def oracle(value): return value == 1")
        producer_source = _write_artifact(tmp_path, f"{run_id}/producer_source.py", "def producer(value): return value + 0")
        artifacts = {
            "fixture": _write_artifact(tmp_path, f"{run_id}/fixture.json", {
                "case_id": case_id, "run_id": run_id, "fixture_id": "fixture-v1",
                "run_kind": kind, "input": input_value, "control": control,
            }),
            "environment": _write_artifact(tmp_path, f"{run_id}/environment.json", {
                "case_id": case_id, "run_id": run_id, "environment_id": "pytest-local",
                "isolation": {"mode": "FRESH_PROCESS_TEMPORARY_WORKSPACE", "process_isolated": True,
                              "workspace_ephemeral": True, "cwd_isolated": True, "home_isolated": True,
                              "tmp_isolated": True, "sandbox": False},
            }),
            "procedure": _write_artifact(tmp_path, f"{run_id}/procedure.json", {
                "case_id": case_id, "run_id": run_id, "steps": ["invoke", "observe"],
            }),
            "control_spec": _write_artifact(tmp_path, f"{run_id}/control_spec.json", {
                "case_id": case_id, "run_id": run_id, "run_kind": kind, "control": control,
            }),
            "stdout": _write_artifact(tmp_path, f"{run_id}/stdout.txt", "execution output"),
            "stderr": _write_artifact(tmp_path, f"{run_id}/stderr.txt", ""),
            "observed": _write_artifact(tmp_path, f"{run_id}/observed.json", {
                "case_id": case_id, "run_id": run_id, "value": "observed",
            }),
            "oracle": _write_artifact(tmp_path, f"{run_id}/oracle.json", {
                "case_id": case_id, "run_id": run_id, "independent": True,
                "producer_used_as_oracle": False, "oracle_module": "oracle_impl",
                "producer_module": "producer_impl", "oracle_source_sha256": oracle_source["sha256"],
                "producer_source_sha256": producer_source["sha256"], "result": "PASS",
            }),
            "oracle_source": oracle_source,
            "producer_source": producer_source,
            "metrics": _write_artifact(tmp_path, f"{run_id}/metrics.json", {
                "case_id": case_id, "run_id": run_id, "duration_ms": 1,
            }),
        }
        run = {
            "kind": kind, "run_id": run_id, "case_id": case_id,
            "clean_state": True, "execution_status": "PASS", "exit_code": 0,
            "agent_version": "test-agent-1", "executor_version": "test-executor-1",
            "machinery": "pytest-test-fixture", "started": 1.0, "ended": 2.0,
            "artifacts": artifacts,
        }
        (repetitions if kind == "NORMAL" else controls).append(run)
    row = {
        "CASE_ID": case_id, "execution_status": "PASS", "contract_status": "PASS",
        "repetitions": repetitions, "controls": controls,
    }
    row["independent_validation"] = independently_validate_case(row, tmp_path)
    return row

def test_population_intersection_is_exact():
    report = intersection()
    assert report["helper_records"] == 106
    assert report["helper_criterion_met"] == 103
    assert report["helper_blocked"] == 3
    assert report["met_inside_m0_fail"] == 83
    assert report["met_inside_m0_pass"] == 20
    assert report["blocked_inside_m0_fail"] == 3
    assert report["m0_fail_without_helper"] == 894
    assert report["identity"] == "83 + 3 + 894 = 980"
    assert report["contractual_pass"] == 0


def test_withdrawn_claims_stay_out_of_contractual_pass():
    by_id = {row["CASE_ID"]: row for row in amendments()}
    assert len(by_id) == 106
    for case_id in ("MGL5-INF-0106", "MGL5-INF-0109", "MGL5-INF-0632"):
        assert by_id[case_id]["S4_HELPER_RESULT"] == "CRITERION_MET"
        assert by_id[case_id]["HELPER_DISPOSITION"] == "WITHDRAWN"
        assert by_id[case_id]["CONTRACTUAL_RESULT"] == "BLOCKED"
        assert by_id[case_id]["ROOT_CAUSE"]


def test_investigation_flag_cannot_turn_not_run_into_c05():
    rows = _population("NOT_RUN", individual_investigation=True)
    verdict = validate(rows)
    assert verdict["c05_passed"] is False
    assert verdict["c05_status"] == "NOT_PASSED"
    assert verdict["not_run"] == 1000
    assert verdict["authentic_results"] == 0
    assert verdict["not_run_counts_as_execution"] is False
    assert "investigation-is-not-execution" in verdict["rejected"][0]["reasons"]
    assert "evidence-root-not-supplied" in verdict["rejected"][0]["reasons"]
    assert len(verdict["rejected"]) == 1000


def test_inline_self_hashed_payload_is_not_execution_evidence():
    rows = _population("FAIL", evidence_payload="FAIL:1", evidence_sha256=hashlib.sha256(b"FAIL:1").hexdigest())
    verdict = validate(rows)
    assert verdict["c05_passed"] is False
    assert verdict["authentic_results"] == 0
    assert "exactly-three-normal-repetitions-required" in verdict["rejected"][0]["reasons"]


def test_real_persisted_artifacts_are_verified_for_a_dossier(tmp_path):
    row = _valid_row_with_artifacts(tmp_path)
    assert _validate_row(row, tmp_path) == []


def test_artifact_tampering_is_detected(tmp_path):
    row = _valid_row_with_artifacts(tmp_path)
    artifact = row["repetitions"][0]["artifacts"]["observed"]
    (tmp_path / artifact["path"]).write_text('{"tampered":true}', encoding="utf-8")
    errors = _validate_row(row, tmp_path)
    assert any("artifact-digest-mismatch" in error for error in errors)


def test_contract_status_cannot_contradict_execution():
    row = {"execution_status": "FAIL", "contract_status": "PASS"}
    assert "fail-promoted-to-contract-pass" in contradictions(row)
    assert "non-success-promoted-to-contract-pass" in contradictions(
        {"execution_status": "BLOCKED", "contract_status": "PASS"}
    )


def test_oracle_must_be_independent_and_bound_to_case_and_run(tmp_path):
    row = _valid_row_with_artifacts(tmp_path)
    oracle = row["repetitions"][0]["artifacts"]["oracle"]
    payload = {"case_id": row["CASE_ID"], "run_id": row["repetitions"][0]["run_id"],
               "independent": False, "producer_used_as_oracle": True, "result": "PASS"}
    path = tmp_path / oracle["path"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    oracle["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    errors = _validate_row(row, tmp_path)
    assert "oracle-not-independent" in errors
    assert "oracle-circular" in errors


def test_repetition_and_run_id_requirements_are_enforced(tmp_path):
    row = _valid_row_with_artifacts(tmp_path)
    row["repetitions"][1]["run_id"] = row["repetitions"][0]["run_id"]
    errors = _validate_row(row, tmp_path)
    assert "duplicate-run-id-within-case" in errors


def test_missing_environment_and_clean_state_are_rejected(tmp_path):
    row = _valid_row_with_artifacts(tmp_path)
    row["repetitions"][0]["clean_state"] = False
    row["repetitions"][0]["artifacts"].pop("environment")
    errors = _validate_row(row, tmp_path)
    assert "clean-state-not-proven" in errors
    assert "artifact-environment-missing" in errors


def test_cross_case_run_id_reuse_is_detected():
    rows = _population("NOT_RUN")
    rows[0] = {"CASE_ID": "MGL5-INF-0001", "execution_status": "FAIL",
               "contract_status": "FAIL", "repetitions": [{"run_id": "run-duplicate-0001"}]}
    rows[1] = {"CASE_ID": "MGL5-INF-0002", "execution_status": "FAIL",
               "contract_status": "FAIL", "repetitions": [{"run_id": "run-duplicate-0001"}]}
    verdict = validate(rows)
    assert any("run-id-reused-across-cases" in item["reasons"] for item in verdict["rejected"])


def test_population_and_historical_claims_remain_unaccredited():
    rows = _population("NOT_RUN")
    assert validate(rows)["c05_passed"] is False
    assert manifest()["c05_status"] == "NOT_PASSED"
    assert manifest()["global_condition_counter"] == "4/26"


def test_evidence_paths_cannot_be_reused_between_repetitions(tmp_path):
    row = _valid_row_with_artifacts(tmp_path)
    first = row["repetitions"][0]["artifacts"]["fixture"]
    row["repetitions"][1]["artifacts"]["fixture"] = dict(first)
    rows = _population("NOT_RUN")
    rows[0] = row
    verdict = validate(rows, evidence_root=tmp_path)
    reasons = verdict["rejected"][0]["reasons"]
    assert any(reason.startswith("evidence-path-reused:") for reason in reasons)


def test_relabeling_same_input_as_negative_and_boundary_is_rejected(tmp_path):
    row = _valid_row_with_artifacts(tmp_path)
    first = row["repetitions"][0]["artifacts"]["fixture"]
    second = row["controls"][0]["artifacts"]["fixture"]
    source = json.loads((tmp_path / first["path"]).read_text(encoding="utf-8"))
    target_path = tmp_path / second["path"]
    target = json.loads(target_path.read_text(encoding="utf-8"))
    target["input"] = source["input"]
    target_path.write_text(json.dumps(target, sort_keys=True), encoding="utf-8")
    second["sha256"] = hashlib.sha256(target_path.read_bytes()).hexdigest()
    errors = _validate_row(row, tmp_path)
    assert "negative-and-boundary-inputs-must-be-distinct" in errors
