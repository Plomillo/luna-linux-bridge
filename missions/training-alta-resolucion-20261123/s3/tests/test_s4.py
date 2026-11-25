import pytest

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
    assert authorize("cidr_bounds") == "AUTHORIZED"
