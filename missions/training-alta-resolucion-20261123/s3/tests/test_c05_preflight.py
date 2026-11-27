from __future__ import annotations

import pytest

from metagente_luna_s3.registry import EXECUTORS, ORACLES, REGISTRY
from metagente_luna_s4.c05_preflight import blocked_preflight_probe
from metagente_luna_s4.c05_preflight_oracle import blocked_preflight_oracle
from metagente_luna_s4.controls import accepts
from metagente_luna_s4.runner import _execute


def _arguments(phase: str) -> dict:
    return {
        "case_id": "MGL5-INF-0100",
        "blocker_code": "NO_COMPLETE_EXECUTION_PLAN",
        "phase": phase,
        "details": "No source-grounded plan and controls are registered; operation not invoked.",
    }


def test_preflight_blocker_is_registered_with_distinct_producer_and_oracle():
    capability = REGISTRY["c05_preflight_blocked"]
    producer = EXECUTORS["c05_preflight_blocked"]
    oracle = ORACLES[capability.oracle_id]

    assert capability.status == "TESTED"
    assert producer.__module__ != oracle.__module__


def test_preflight_blocked_result_is_not_promoted_to_operation_pass():
    arguments = _arguments("NORMAL_PLAN")
    observed = blocked_preflight_probe(**arguments)
    verdict = blocked_preflight_oracle(arguments, observed)

    assert observed["blocked"] is True
    assert observed["operation_invoked"] is False
    assert verdict["ok"] is None
    assert verdict["underlying_operation_result"] == "NOT_OBSERVED"


def test_runner_preserves_preflight_blocked_as_blocked():
    record = _execute(
        "c05_preflight_blocked",
        _arguments("NORMAL_PLAN"),
        "MGL5-INF-0100",
        backend="DOCKER_RESTRICTED_CONTAINER",
    )

    assert record["execution_status"] == "BLOCKED"
    assert record["oracle_result"]["ok"] is None
    assert record["observed"]["operation_invoked"] is False


@pytest.mark.parametrize("phase", ["NEGATIVE_CONTROL", "BOUNDARY_CONTROL"])
def test_blocked_control_is_accepted_only_as_a_blocked_preflight(phase: str):
    observed = blocked_preflight_probe(**_arguments(phase))

    assert accepts("preflight-blocked", observed, "BLOCKED") is True
    assert accepts("preflight-blocked", observed, "PASS") is False
    assert accepts("preflight-blocked", observed, "FAIL") is False


def test_preflight_blocker_rejects_noncanonical_phase():
    with pytest.raises(ValueError, match="invalid preflight phase"):
        blocked_preflight_probe(
            "MGL5-INF-0100",
            "NO_COMPLETE_EXECUTION_PLAN",
            "NORMAL",
            "missing plan",
        )
