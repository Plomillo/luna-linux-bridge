import hashlib
import json

import pytest

from metagente_luna_s4.evidence import assemble_case_record, persist_run


def test_persist_run_writes_byte_hashed_artifacts_without_certifying(tmp_path):
    record = {
        "case_id": "MGL5-INF-0001",
        "run_id": "run-evidence-0001",
        "capability_id": "utf8_roundtrip",
        "execution_status": "PASS",
        "exit_code": 0,
        "stdout": "ok",
        "stderr": "",
        "observed": {"text": "Luna"},
        "oracle_result": {"ok": True},
        "started": 1.0,
        "ended": 2.0,
        "oracle_module": "metagente_luna_s3.d01_oracle",
        "producer_module": "metagente_luna_s3.d01_exec",
        "agent_version": "0.1.0",
        "executor_version": "1",
        "machinery": "LOCAL_TEST_ONLY",
    }
    result = persist_run(record, {"text": "Luna"}, tmp_path)
    assert result["evidence_status"] == "PERSISTED_NOT_INDEPENDENTLY_VALIDATED"
    assert result["clean_state"] is False
    assert result["independent_validation"]["passed"] is False
    assert result["execution_status"] == "PASS"
    assert set(result["artifacts"]) == {
        "fixture", "environment", "procedure", "stdout",
        "stderr", "observed", "oracle", "metrics", "oracle_source", "producer_source", "control_spec",
    }
    for artifact in result["artifacts"].values():
        path = tmp_path / artifact["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    oracle_path = tmp_path / result["artifacts"]["oracle"]["path"]
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    assert oracle["independent"] is True
    assert oracle["case_id"] == record["case_id"]


def test_persist_run_never_overwrites_an_existing_run(tmp_path):
    record = {"case_id": "MGL5-INF-0001", "run_id": "run-evidence-0002"}
    persist_run(record, {}, tmp_path)
    with pytest.raises(FileExistsError):
        persist_run(record, {}, tmp_path)


def test_persist_run_rejects_path_traversal_case_id(tmp_path):
    record = {"case_id": "../../outside", "run_id": "run-evidence-0003"}
    with pytest.raises(ValueError):
        persist_run(record, {}, tmp_path)


def test_runner_persists_observed_execution_but_does_not_claim_clean_state(tmp_path):
    from metagente_luna_s4.runner import execute

    record = execute(
        "utf8_roundtrip",
        {"text": "Luna"},
        "MGL5-INF-0001",
        evidence_root=str(tmp_path),
        run_kind="NORMAL",
    )
    assert record["lifecycle_status"] == "EXECUTED"
    assert record["execution_status"] == "PASS"
    assert record["contract_status"] == "NOT_A_PASS"
    assert record["persisted_evidence"]["clean_state"] is False
    assert record["persisted_evidence"]["independent_validation"]["passed"] is False
    assert record["persisted_evidence"]["evidence_status"] == "PERSISTED_NOT_INDEPENDENTLY_VALIDATED"


def test_assembler_requires_three_distinct_run_kinds(tmp_path):
    from metagente_luna_s4.runner import execute

    runs = [
        execute("utf8_roundtrip", {"text": "Luna"}, "MGL5-INF-0001",
                evidence_root=str(tmp_path), run_kind="NORMAL"),
        execute("utf8_reject_invalid", {"payload_hex": "80"}, "MGL5-INF-0001",
                evidence_root=str(tmp_path), run_kind="NEGATIVE",
                control_metadata={"definition": "isolated continuation byte", "expected_behavior": "reject invalid UTF-8", "source": "test-spec"}),
        execute("utf8_roundtrip", {"text": ""}, "MGL5-INF-0001",
                evidence_root=str(tmp_path), run_kind="BOUNDARY",
                control_metadata={"definition": "empty string boundary", "expected_behavior": "round-trip empty text", "source": "test-spec"}),
    ]
    row = assemble_case_record("MGL5-INF-0001", runs)
    assert row["CASE_ID"] == "MGL5-INF-0001"
    assert row["execution_status"] == "PASS"
    assert row["contract_status"] == "NOT_A_PASS"
    assert len(row["repetitions"]) == 3
    assert {item["kind"] for item in row["repetitions"]} == {"NORMAL", "NEGATIVE", "BOUNDARY"}
    assert all(item["clean_state"] is False for item in row["repetitions"])


def test_assembler_rejects_missing_negative_or_boundary_run(tmp_path):
    from metagente_luna_s4.runner import execute

    runs = [
        execute("utf8_roundtrip", {"text": "Luna"}, "MGL5-INF-0001",
                evidence_root=str(tmp_path), run_kind="NORMAL")
    ]
    with pytest.raises(ValueError, match="exactly one NORMAL"):
        assemble_case_record("MGL5-INF-0001", runs)
