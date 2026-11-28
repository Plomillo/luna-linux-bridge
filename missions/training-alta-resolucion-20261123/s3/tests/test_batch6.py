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
    assert set(by_id) == {"MGL5-INF-0105", "MGL5-INF-0106", "MGL5-INF-0109", "MGL5-INF-0111", "MGL5-INF-0114", "MGL5-INF-0115", "MGL5-INF-0116", "MGL5-INF-0117", "MGL5-INF-0118", "MGL5-INF-0609", "MGL5-INF-0611", "MGL5-INF-0632"}
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


def test_registered_d03_plans_have_oracles_and_controls():
    # All source cases resolve to the corrected executor contracts.
    from metagente_luna_s3.batch6_exec import (
        avl_tree,
        bellman_ford_cycle,
        bst_inorder,
        determinant_3x3,
        dfs_graph,
        dijkstra,
        fifo_queue,
        linear_search_complexity,
        linked_list,
        matrix_multiply,
        moving_average,
        shortest_path,
    )
    from metagente_luna_s3.batch6_oracle import (
        avl_tree_oracle,
        bellman_ford_cycle_oracle,
        bst_inorder_oracle,
        determinant_3x3_oracle,
        dfs_graph_oracle,
        dijkstra_oracle,
        fifo_queue_oracle,
        linear_search_complexity_oracle,
        linked_list_oracle,
        matrix_multiply_oracle,
        moving_average_oracle,
        shortest_path_oracle,
    )
    from metagente_luna_s4.batch3 import CASES as BATCH3_CASES
    from metagente_luna_s4.batch5 import CASES as BATCH5_CASES
    from metagente_luna_s4.controls import run_controls

    specs = {item["case_id"]: item for item in [*BATCH3_CASES, *BATCH5_CASES, *CASES]}
    queue_args = specs["MGL5-INF-0110"]["arguments"]
    queue_result = fifo_queue(**queue_args)
    assert queue_result["dequeued"] == ["A", "B", "C"]
    assert fifo_queue_oracle(queue_args, queue_result)["ok"]

    bst_args = specs["MGL5-INF-0112"]["arguments"]
    bst_result = bst_inorder(**bst_args)
    assert bst_result["inorder"] == [1, 3, 6, 8, 10, 14]
    assert bst_inorder_oracle(bst_args, bst_result)["ok"]

    avl_args = specs["MGL5-INF-0113"]["arguments"]
    avl_result = avl_tree(**avl_args)
    assert avl_result["balanced"] is True and avl_result["height"] <= 10
    assert avl_result["inorder"] == list(range(1, 1001))
    assert avl_tree_oracle(avl_args, avl_result)["ok"]

    linked_args = specs["MGL5-INF-0111"]["arguments"]
    linked_result = linked_list(**linked_args)
    assert linked_result["values"] == [1, 3] and linked_result["length"] == 2
    assert linked_list_oracle(linked_args, linked_result)["ok"]

    dfs_args = specs["MGL5-INF-0115"]["arguments"]
    dfs_result = dfs_graph(**dfs_args)
    assert dfs_result["order"] == ["A", "B", "C", "D"] and dfs_result["cycle"] is True
    assert dfs_graph_oracle(dfs_args, dfs_result)["ok"]

    bfs_args = specs["MGL5-INF-0114"]["arguments"]
    bfs_result = shortest_path(**bfs_args)
    assert bfs_result["path"] == ["A", "B", "D", "E", "F"]
    assert shortest_path_oracle(bfs_args, bfs_result)["ok"]

    dij_args = specs["MGL5-INF-0116"]["arguments"]
    dij_result = dijkstra(**dij_args)
    assert dij_result["distance"] == 4 and dij_result["path"] == ["A", "C", "B", "D"]
    assert dijkstra_oracle(dij_args, dij_result)["ok"]
    negative_args = specs["MGL5-INF-0117"]["arguments"]
    negative_result = dijkstra(**negative_args)
    assert negative_result["rejected"] is True and dijkstra_oracle(negative_args, negative_result)["ok"]

    bell_args = specs["MGL5-INF-0118"]["arguments"]
    bell_result = bellman_ford_cycle(**bell_args)
    assert bell_result["negative_cycle_reachable"] is True and bell_result["distances"] is None
    assert bellman_ford_cycle_oracle(bell_args, bell_result)["ok"]

    matrix_args = specs["MGL5-INF-0609"]["arguments"]
    matrix_result = matrix_multiply(**matrix_args)
    assert matrix_result["result"] == [[58, 64], [139, 154]]
    assert matrix_multiply_oracle(matrix_args, matrix_result)["ok"]

    determinant_args = specs["MGL5-INF-0611"]["arguments"]
    determinant_result = determinant_3x3(**determinant_args)
    assert determinant_result["determinant"] == -306
    assert determinant_3x3_oracle(determinant_args, determinant_result)["ok"]

    moving_args = specs["MGL5-INF-0632"]["arguments"]
    moving_result = moving_average(**moving_args)
    assert moving_result["averages"] == [2.0, 3.0, 4.0, 5.0]
    assert moving_average_oracle(moving_args, moving_result)["ok"]

    linear_args = specs["MGL5-INF-0119"]["arguments"]
    linear_result = linear_search_complexity(**linear_args)
    assert [row["comparisons"] for row in linear_result["measurements"]] == [1000, 2000, 4000]
    assert linear_result["growth_ratios"] == [2.0, 2.0]
    assert linear_search_complexity_oracle(linear_args, linear_result)["ok"]

    control_rows = {row["case_id"]: row["controls"] for row in run_controls()}
    for case_id in ("MGL5-INF-0110", "MGL5-INF-0111", "MGL5-INF-0112", "MGL5-INF-0113", "MGL5-INF-0114", "MGL5-INF-0115", "MGL5-INF-0116", "MGL5-INF-0117", "MGL5-INF-0118", "MGL5-INF-0119", "MGL5-INF-0609", "MGL5-INF-0611", "MGL5-INF-0632"):
        assert all(control["accepted"] for control in control_rows[case_id].values())



def test_interpreter_resolves_all_registered_fixture_candidates():
    expected = {
        "MGL5-INF-0105": "stable_ages", "MGL5-INF-0106": "descending_seed", "MGL5-INF-0109": "stack_sequence",
        "MGL5-INF-0110": "fifo_queue", "MGL5-INF-0111": "linked_list", "MGL5-INF-0112": "bst_inorder",
        "MGL5-INF-0113": "avl_tree", "MGL5-INF-0114": "shortest_path", "MGL5-INF-0115": "dfs_graph",
        "MGL5-INF-0116": "dijkstra", "MGL5-INF-0117": "dijkstra", "MGL5-INF-0118": "bellman_ford_cycle",
        "MGL5-INF-0119": "linear_search_complexity", "MGL5-INF-0609": "matrix_multiply",
        "MGL5-INF-0611": "determinant_3x3", "MGL5-INF-0632": "moving_average_c05",
    }
    for case_id, operation in OPERATIONS:
        result = interpret(operation)
        assert result.status == "READY" and result.intent == expected[case_id]
        assert all(argument.provenance == "FIXTURE" for argument in result.arguments)


