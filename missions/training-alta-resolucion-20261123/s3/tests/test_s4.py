from pathlib import Path

import pytest

from metagente_luna_s3.evidence import verify_run, write_run
from metagente_luna_s3.planner import plan_for
from metagente_luna_s4.guard import authorize, require_case_id
from metagente_luna_s4.provider import UnavailableProvider
from metagente_luna_s4.runner import execute


def test_remote_provider_does_not_invent_an_interpretation():
    result = UnavailableProvider().interpret("Calcular red y broadcast de 192.0.2.130/26.")
    assert result["status"] == "UNAVAILABLE"
    assert result["interpretation"] is None


def test_runner_rejects_an_unknown_capability_and_does_not_pass_it():
    record = execute("not-a-capability", {}, "MGL5-INF-0254")
    assert record["execution_status"] == "REJECTED"
    assert record["contract_status"] == "NOT_A_PASS"
    assert record["stdout"] == ""
    assert record["observed"] is None


def test_runner_executes_the_registered_cidr_capability():
    record = execute("cidr_bounds", {"cidr": "192.0.2.130/26"}, "MGL5-INF-0254")
    assert record["execution_status"] == "EXECUTED"
    assert record["exit_code"] == 0
    assert record["observed"]["network"] == "192.0.2.128"
    assert record["contract_status"] == "NOT_A_PASS"


def test_schema_rejects_a_missing_argument():
    record = execute("cidr_bounds", {}, "MGL5-INF-0254")
    assert record["execution_status"] == "REJECTED"


def test_path_traversal_is_rejected():
    with pytest.raises(ValueError):
        require_case_id("../etc/passwd")
    assert require_case_id("MGL5-INF-0254") == "MGL5-INF-0254"


def test_unknown_capability_is_not_authorized():
    with pytest.raises(KeyError):
        authorize("shell")
    assert authorize("cidr_bounds") == "AUTHORIZED_LOCAL_TEST_ONLY"


def test_execute_rejects_a_traversing_case_id_before_running():
    record = execute("cidr_bounds", {"cidr": "192.0.2.130/26"}, "../etc/passwd")
    assert record["execution_status"] == "REJECTED"
    assert record["observed"] is None


def test_missing_sandbox_blocks_production_execution():
    record = execute("cidr_bounds", {"cidr": "192.0.2.130/26"}, "MGL5-INF-0254", backend="ISOLATED_SANDBOX")
    assert record["execution_status"] == "BLOCKED"
    assert record["observed"] is None


def test_local_run_keeps_an_independent_oracle_and_is_not_a_pass():
    record = execute("cidr_bounds", {"cidr": "192.0.2.130/26"}, "MGL5-INF-0254")
    assert record["authorization"] == "AUTHORIZED_LOCAL_TEST_ONLY"
    assert record["backend"] == "LOCAL_TEST_ONLY"
    assert record["oracle_result"]["ok"] is True
    assert record["contract_status"] == "NOT_A_PASS"


def test_evidence_rejects_traversal_and_checks_its_own_hashes(tmp_path: Path):
    with pytest.raises(ValueError):
        write_run(tmp_path, "../MGL5-INF-0001", "run-1", {"observed.json": {"ok": True}})
    folder = write_run(tmp_path, "MGL5-INF-0254", "run-1", {"observed.json": {"network": "192.0.2.128"}})
    assert verify_run(folder, tmp_path) == "EVIDENCE_VALIDATED"
    (folder / "observed.json").write_text("{}\n", encoding="utf-8")
    assert verify_run(folder, tmp_path) == "EVIDENCE_CORRUPTED"


def test_plan_is_not_ready_for_an_unregistered_capability():
    assert plan_for("p", "shell").status == "NOT_EXECUTABLE"
    assert plan_for("p", "cidr_bounds").status == "READY"


def test_historical_cidr_evidence_still_matches_its_manifest():
    folder = Path(__file__).parents[1] / "evidence" / "MGL5-INF-0254" / "run-1"
    assert verify_run(folder, folder.parents[1]) == "EVIDENCE_VALIDATED"
