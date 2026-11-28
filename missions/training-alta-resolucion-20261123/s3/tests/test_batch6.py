from __future__ import annotations

from metagente_luna_s3.batch5_exec import descending_seed
from metagente_luna_s3.batch5_oracle import seed_permutation
from metagente_luna_s3.batch6_exec import stable_ages, stack_sequence
from metagente_luna_s3.batch6_oracle import (
    stable_ages_oracle,
    stack_sequence_oracle,
)
from metagente_luna_s3.interpret import interpret
from metagente_luna_s4.batch6 import CASES, OPERATIONS
from metagente_luna_s4.controls import accepts


def test_batch6_cases_are_typed_source_grounded_plans():
    by_id = {case["case_id"]: case for case in CASES}
    assert set(by_id) == {"MGL5-INF-0105", "MGL5-INF-0106", "MGL5-INF-0109", "MGL5-INF-0110", "MGL5-INF-0111", "MGL5-INF-0112", "MGL5-INF-0114", "MGL5-INF-0115", "MGL5-INF-0609", "MGL5-INF-0611", "MGL5-INF-0632"}
    assert by_id["MGL5-INF-0105"]["fixture_provenance"].endswith("#stable-ages")
    assert by_id["MGL5-INF-0109"]["fixture_provenance"].endswith("#stack-script")
    assert by_id["MGL5-INF-0106"]["fixture_provenance"].endswith("#ten-thousand; seed/count drive deterministic integer generation")
    assert by_id["MGL5-INF-0106"]["arguments"] == {"seed": 106, "count": 10_000}
    for case_id, instruction in OPERATIONS:
        if case_id not in by_id:
            continue
        result = interpret(instruction)
        if case_id == "MGL5-INF-0106":
            assert result.status == "READY"
            assert result.intent == "descending_seed"
            assert {argument.name: argument.value for argument in result.arguments} == {"seed": 106, "count": 10_000}
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

def test_four_new_d03_candidates_are_registered_oracled_and_controlled():
    from metagente_luna_s3.batch6_exec import (
        determinant_3x3,
        matrix_multiply,
        moving_average,
        shortest_path,
    )
    from metagente_luna_s3.batch6_oracle import (
        determinant_3x3_oracle,
        matrix_multiply_oracle,
        moving_average_oracle,
        shortest_path_oracle,
    )
    from metagente_luna_s4.batch6 import CASES as BATCH6_CASES
    from metagente_luna_s4.controls import run_controls

    specs = {item["case_id"]: item for item in BATCH6_CASES}
    graph = specs["MGL5-INF-0114"]["arguments"]
    graph_result = shortest_path(**graph)
    assert graph_result == {"rejected": False, "reachable": True, "path": ["A", "B", "D", "E", "F"], "distance": 4}
    assert shortest_path_oracle(graph, graph_result)["ok"] is True

    product = specs["MGL5-INF-0609"]["arguments"]
    product_result = matrix_multiply(**product)
    assert product_result["result"] == [[58, 64], [139, 154]]
    assert matrix_multiply_oracle(product, product_result)["ok"] is True

    determinant = specs["MGL5-INF-0611"]["arguments"]
    determinant_result = determinant_3x3(**determinant)
    assert determinant_result["determinant"] == -306
    assert determinant_3x3_oracle(determinant, determinant_result)["ok"] is True

    series = specs["MGL5-INF-0632"]["arguments"]
    series_result = moving_average(**series)
    assert series_result["averages"] == [2.0, 3.0, 4.0, 5.0]
    assert moving_average_oracle(series, series_result)["ok"] is True

    controls = {row["case_id"]: row["controls"] for row in run_controls()}
    for case_id in ("MGL5-INF-0114", "MGL5-INF-0609", "MGL5-INF-0611", "MGL5-INF-0632"):
        assert controls[case_id]["negative"]["accepted"] is True
        assert controls[case_id]["boundary"]["accepted"] is True
        assert controls[case_id]["negative"]["run_kind"] == "NEGATIVE"
        assert controls[case_id]["boundary"]["run_kind"] == "BOUNDARY"


def test_interpreter_resolves_new_fixture_backed_d03_operations():
    for case_id, operation in OPERATIONS:
        if case_id not in {"MGL5-INF-0106", "MGL5-INF-0110", "MGL5-INF-0111", "MGL5-INF-0112", "MGL5-INF-0114", "MGL5-INF-0115", "MGL5-INF-0609", "MGL5-INF-0611", "MGL5-INF-0632"}:
            continue
        result = interpret(operation)
        assert result.status == "READY"
        assert result.intent in {"descending_seed", "shortest_path", "matrix_multiply", "determinant_3x3", "moving_average", "moving_average_c05"}
        assert all(argument.provenance == "FIXTURE" for argument in result.arguments)

def test_fifo_bst_dfs_linked_list_have_independent_oracles_and_controls():
    from metagente_luna_s3.batch6_exec import fifo_queue, bst_inorder, dfs_graph, linked_list
    from metagente_luna_s3.batch6_oracle import fifo_queue_oracle, bst_inorder_oracle, dfs_graph_oracle, linked_list_oracle
    from metagente_luna_s4.controls import run_controls

    specs = {case["case_id"]: case for case in CASES}
    qargs = specs["MGL5-INF-0110"]["arguments"]
    qresult = fifo_queue(**qargs)
    assert qresult["dequeued"] == ["A", "B", "C"] and fifo_queue_oracle(qargs, qresult)["ok"]

    bargs = specs["MGL5-INF-0112"]["arguments"]
    bresult = bst_inorder(**bargs)
    assert bresult["inorder"] == [1, 3, 6, 8, 10, 14] and bst_inorder_oracle(bargs, bresult)["ok"]

    dargs = specs["MGL5-INF-0115"]["arguments"]
    dresult = dfs_graph(**dargs)
    assert dresult["order"] == ["A", "B", "C", "D"] and dresult["cycle"] is True
    assert dfs_graph_oracle(dargs, dresult)["ok"]

    largs = specs["MGL5-INF-0111"]["arguments"]
    lresult = linked_list(**largs)
    assert lresult["values"] == [1, 3] and lresult["length"] == 2 and linked_list_oracle(largs, lresult)["ok"]

    controls = {row["case_id"]: row["controls"] for row in run_controls()}
    for case_id in ("MGL5-INF-0110", "MGL5-INF-0111", "MGL5-INF-0112", "MGL5-INF-0115"):
        assert all(control["accepted"] for control in controls[case_id].values())


def test_interpreter_resolves_four_new_fixture_operations():
    expected = {"MGL5-INF-0110": "fifo_queue", "MGL5-INF-0111": "linked_list", "MGL5-INF-0112": "bst_inorder", "MGL5-INF-0115": "dfs_graph"}
    for case_id, operation in OPERATIONS:
        if case_id not in expected:
            continue
        plan = interpret(operation)
        assert plan.status == "READY" and plan.intent == expected[case_id]
        assert all(argument.provenance == "FIXTURE" for argument in plan.arguments)
