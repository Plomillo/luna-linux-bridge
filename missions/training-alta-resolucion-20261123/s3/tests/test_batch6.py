from __future__ import annotations

from metagente_luna_s3.batch5_exec import descending_seed
from metagente_luna_s3.batch6_exec import stable_ages, stack_sequence
from metagente_luna_s3.batch5_oracle import seed_permutation
from metagente_luna_s3.batch6_oracle import (
    stable_ages_oracle,
    stack_sequence_oracle,
)
from metagente_luna_s3.interpret import interpret
from metagente_luna_s4.batch6 import CASES, OPERATIONS
from metagente_luna_s4.controls import accepts


def test_batch6_cases_are_typed_source_grounded_plans():
    by_id = {case["case_id"]: case for case in CASES}
    assert set(by_id) == {"MGL5-INF-0105", "MGL5-INF-0106", "MGL5-INF-0109"}
    assert by_id["MGL5-INF-0105"]["fixture_provenance"].endswith("#stable-ages")
    assert by_id["MGL5-INF-0109"]["fixture_provenance"].endswith("#stack-script")
    assert by_id["MGL5-INF-0106"]["fixture_provenance"].endswith("#ten-thousand; seed/count drive deterministic integer generation")
    assert by_id["MGL5-INF-0106"]["arguments"] == {"seed": 106, "count": 10_000}
    for case_id, instruction in OPERATIONS:
        if case_id not in by_id:
            continue
        result = interpret(instruction)
        if case_id == "MGL5-INF-0106":
            # The language interpreter correctly refuses to invent the 10,000
            # values; the separately authored, seeded fixture supplies them.
            assert result.status == "BLOCKED"
            assert result.missing == ["input-integers"]
            continue
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


def test_descending_sort_checks_permutation_order_and_rejection_controls():
    from metagente_luna_s4.batch6 import CASES as BATCH6_CASES

    spec = next(item for item in BATCH6_CASES if item["case_id"] == "MGL5-INF-0106")
    arguments = spec["arguments"]
    observed = descending_seed(**arguments)
    ordered = observed["ordered"]
    assert len(ordered) == observed["length"] == 10_000
    assert all(ordered[index] >= ordered[index + 1] for index in range(len(ordered) - 1))
    assert seed_permutation(arguments, observed)["ok"] is True

    invalid = {"seed": 106, "count": -1}
    rejected = descending_seed(**invalid)
    assert accepts("rejected", rejected, "EXECUTED") is True
    assert seed_permutation(invalid, rejected)["ok"] is True

    boundary = {"seed": 106, "count": 1}
    boundary_result = descending_seed(**boundary)
    assert accepts("descending-seed-singleton", boundary_result, "EXECUTED") is True
    assert seed_permutation(boundary, boundary_result)["ok"] is True
