from metagente_luna_s3.interpret import interpret
from metagente_luna_s3.ir import Provenance
from metagente_luna_s4.batch6 import run_all
from metagente_luna_s4.runner import execute


def test_search_does_not_need_the_case_id():
    literal = interpret("Buscar 7 en [2,7,9,7].")
    paraphrase = interpret("Localizar la primera aparición de 7 en [2, 7, 9, 7].")
    unseen = interpret("Hallar el primer índice de 4 dentro de la secuencia [9, 4, 4, 1].")
    assert literal.intent == paraphrase.intent == unseen.intent == "first_match"
    assert {item.name: item.value for item in literal.arguments} == {"needle": 7, "values": [2, 7, 9, 7]}
    assert all(item.provenance is Provenance.SOURCE_INSTRUCTION for item in unseen.arguments)


def test_explicit_descending_list_is_a_full_permutation():
    plan = interpret("Reordena de mayor a menor la serie [5, 5, 1, 8].")
    arguments = {item.name: item.value for item in plan.arguments}
    result = execute(plan.intent, arguments, "MGL5-INF-0001")
    assert result["case_id"] == "MGL5-INF-0001"
    assert result["capability_id"] == "descending_values"
    assert result["observed"]["ordered"] == [8, 5, 5, 1]
    assert result["oracle_result"]["ok"] is True


def test_missing_input_is_not_invented():
    thousands = interpret("Ordenar 10.000 enteros en orden descendente.")
    vague = interpret("Ordenar estos valores de mayor a menor.")
    window = interpret("Calcular media móvil de ventana 3 sobre fixture.")
    assert thousands.status == "READY"
    assert thousands.intent == "descending_seed"
    assert {argument.name: argument.value for argument in thousands.arguments} == {"seed": 106, "count": 10_000}
    assert vague.status == "BLOCKED"
    assert window.status == "READY"
    assert window.intent == "moving_average_c05"
    assert {argument.name: argument.value for argument in window.arguments} == {"values": [1, 2, 3, 4, 5, 6], "window": 3}


def test_seven_literal_instructions():
    rows = {row["case_id"]: row for row in run_all()}
    assert rows["MGL5-INF-0105"]["execution_status"] == "CRITERION_MET"
    stable = rows["MGL5-INF-0105"]["observed"]
    # The executor's contract is to preserve complete records, not emit a
    # detached ids-only projection. Verify both sorted order and stable ties.
    assert [record["id"] for record in stable["records"]] == ["b", "d", "a", "c"]
    assert stable["ids_by_age"] == {"20": ["b", "d"], "30": ["a", "c"]}
    assert stable["rejected"] is False
    assert rows["MGL5-INF-0106"]["execution_status"] == "CRITERION_MET"
    assert rows["MGL5-INF-0106"]["observed"]["length"] == 10_000
    assert rows["MGL5-INF-0109"]["execution_status"] == "CRITERION_MET"
    assert rows["MGL5-INF-0109"]["observed"]["events"] == [
        {"operation": "push", "value": 1},
        {"operation": "push", "value": 2},
        {"operation": "peek", "value": 2},
        {"operation": "pop", "value": 2},
        {"operation": "pop", "value": 1},
        {"operation": "underflow", "source": "pop"},
    ]
    assert rows["MGL5-INF-0109"]["observed"]["stack"] == []
    assert rows["MGL5-INF-0109"]["observed"]["underflow_count"] == 1
    assert rows["MGL5-INF-0114"]["execution_status"] == "CRITERION_MET"
    assert rows["MGL5-INF-0609"]["execution_status"] == "CRITERION_MET"
    assert rows["MGL5-INF-0611"]["execution_status"] == "CRITERION_MET"
    assert rows["MGL5-INF-0632"]["execution_status"] == "CRITERION_MET"
    assert rows["MGL5-INF-0106"]["c05_gate"] == "NOT_PASSED"
def test_fifo_bst_dfs_linked_list_source_instructions_execute():
    rows = {row["case_id"]: row for row in run_all()}
    for case_id in ("MGL5-INF-0110", "MGL5-INF-0111", "MGL5-INF-0112", "MGL5-INF-0115"):
        assert rows[case_id]["execution_status"] == "CRITERION_MET"
    assert rows["MGL5-INF-0110"]["observed"]["dequeued"] == ["A", "B", "C"]
    assert rows["MGL5-INF-0112"]["observed"]["inorder"] == [1, 3, 6, 8, 10, 14]
    assert rows["MGL5-INF-0115"]["observed"]["cycle"] is True
    assert rows["MGL5-INF-0111"]["observed"]["values"] == [1, 3]
def test_legacy_batch3_batch5_cases_are_rewired_and_new_batch6_cases_execute():
    from metagente_luna_s4.batch3 import CASES as BATCH3_CASES
    from metagente_luna_s4.batch5 import CASES as BATCH5_CASES
    from metagente_luna_s4.runner import execute

    batch3_spec = next(item for item in BATCH3_CASES if item["case_id"] == "MGL5-INF-0112")
    batch5_specs = {item["case_id"]: item for item in BATCH5_CASES}
    for case_id in ("MGL5-INF-0110", "MGL5-INF-0113", "MGL5-INF-0119"):
        result = execute(batch5_specs[case_id]["capability_id"], batch5_specs[case_id]["arguments"], case_id)
        assert result["execution_status"] == "EXECUTED" and result["oracle_result"]["ok"]
    result = execute(batch3_spec["capability_id"], batch3_spec["arguments"], batch3_spec["case_id"])
    assert result["execution_status"] == "EXECUTED" and result["oracle_result"]["ok"]

    rows = {row["case_id"]: row for row in run_all()}
    for case_id in ("MGL5-INF-0111", "MGL5-INF-0115", "MGL5-INF-0116", "MGL5-INF-0117", "MGL5-INF-0118"):
        assert rows[case_id]["execution_status"] == "CRITERION_MET"
