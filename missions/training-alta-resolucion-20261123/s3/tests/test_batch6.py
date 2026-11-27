from __future__ import annotations

from metagente_luna_s3.batch6_exec import stable_ages, stack_sequence
from metagente_luna_s3.batch6_oracle import stable_ages_oracle, stack_sequence_oracle
from metagente_luna_s3.interpret import interpret
from metagente_luna_s4.batch6 import CASES, OPERATIONS
from metagente_luna_s4.controls import accepts


def test_batch6_cases_are_typed_source_grounded_plans():
    by_id = {case["case_id"]: case for case in CASES}
    assert set(by_id) == {"MGL5-INF-0105", "MGL5-INF-0109"}
    assert by_id["MGL5-INF-0105"]["fixture_provenance"].endswith("#stable-ages")
    assert by_id["MGL5-INF-0109"]["fixture_provenance"].endswith("#stack-script")
    for case_id, instruction in OPERATIONS:
        if case_id in by_id:
            result = interpret(instruction)
            assert result.status == "READY"
            assert result.intent == by_id[case_id]["capability_id"]


def test_stable_age_sort_preserves_equal_age_order_and_rejects_bad_records():
    arguments = {"records": [
        {"id": "a", "age": 30},
        {"id": "b", "age": 20},
        {"id": "c", "age": 30},
        {"id": "d", "age": 20},
    ]}
    observed = stable_ages(**arguments)
    assert [row["id"] for row in observed["records"]] == ["b", "d", "a", "c"]
    assert stable_ages_oracle(arguments, observed)["ok"] is True

    invalid = {"records": [{"id": "", "age": 30}]}
    rejected = stable_ages(**invalid)
    assert accepts("rejected", rejected, "EXECUTED") is True
    assert stable_ages_oracle(invalid, rejected)["ok"] is True

    empty = {"records": []}
    boundary = stable_ages(**empty)
    assert accepts("empty-record-set", boundary, "EXECUTED") is True
    assert stable_ages_oracle(empty, boundary)["ok"] is True


def test_stack_sequence_controls_underflow_and_empty_boundary():
    normal = {"steps": ["push:1", "push:2", "peek", "pop", "pop", "pop"]}
    observed = stack_sequence(**normal)
    assert observed["underflow_count"] == 1
    assert observed["stack"] == []
    assert stack_sequence_oracle(normal, observed)["ok"] is True

    negative = {"steps": ["pop"]}
    negative_result = stack_sequence(**negative)
    assert accepts("single-underflow", negative_result, "EXECUTED") is True
    assert stack_sequence_oracle(negative, negative_result)["ok"] is True

    boundary = {"steps": []}
    boundary_result = stack_sequence(**boundary)
    assert accepts("empty-stack-sequence", boundary_result, "EXECUTED") is True
    assert stack_sequence_oracle(boundary, boundary_result)["ok"] is True
