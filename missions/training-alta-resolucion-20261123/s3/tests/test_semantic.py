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
    assert thousands.status == "BLOCKED"
    assert thousands.missing == ["input-integers"]
    assert thousands.arguments == []
    assert vague.status == "BLOCKED"
    assert window.status == "BLOCKED"
    assert window.missing == ["series-values", "series-length"]


def test_seven_literal_instructions():
    rows = {row["case_id"]: row for row in run_all()}
    assert rows["MGL5-INF-0105"]["execution_status"] == "CRITERION_MET"
    assert rows["MGL5-INF-0105"]["observed"]["ids"] == ["b", "d", "a", "c"]
    assert rows["MGL5-INF-0106"]["execution_status"] == "BLOCKED"
    assert rows["MGL5-INF-0106"]["missing_information"] == ["input-integers"]
    assert rows["MGL5-INF-0109"]["execution_status"] == "CRITERION_MET"
    assert rows["MGL5-INF-0109"]["observed"]["outputs"] == ["pushed", "pushed", 2, 2, 1, "underflow"]
    assert rows["MGL5-INF-0114"]["missing_information"] == ["edges", "endpoints"]
    assert rows["MGL5-INF-0609"]["missing_information"] == ["matrix-entries"]
    assert rows["MGL5-INF-0611"]["missing_information"] == ["reference-matrix"]
    assert rows["MGL5-INF-0632"]["missing_information"] == ["series-values", "series-length"]
    assert rows["MGL5-INF-0106"]["c05_gate"] == "NOT_PASSED"
