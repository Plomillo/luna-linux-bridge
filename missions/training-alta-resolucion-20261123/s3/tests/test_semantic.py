from metagente_luna_s4.batch6 import run_all
from metagente_luna_s4.semantic import interpret


def test_search_does_not_need_the_case_id():
    literal = interpret('Buscar 7 en [2,7,9,7].')
    paraphrase = interpret("Localizar la primera aparición de 7 en [2, 7, 9, 7].")
    assert literal["capability"] == paraphrase["capability"] == "first_match"
    assert literal["arguments"]["needle"] == 7
    assert literal["arguments"]["values"] == [2, 7, 9, 7]


def test_seven_cases_are_executed_or_blocked_from_the_operation():
    rows = run_all()
    by_id = {row["case_id"]: row for row in rows}
    assert by_id["MGL5-INF-0105"]["observed"]["ids"] == ["b", "d", "a", "c"]
    assert by_id["MGL5-INF-0106"]["observed"]["length"] == 10000
    assert by_id["MGL5-INF-0109"]["observed"]["outputs"][-1] == "underflow"
    assert by_id["MGL5-INF-0632"]["execution_status"] == "CRITERION_MET"
    assert by_id["MGL5-INF-0114"]["execution_status"] == "BLOCKED"
    assert by_id["MGL5-INF-0114"]["missing_information"] == ["edges", "endpoints"]
    assert by_id["MGL5-INF-0609"]["missing_information"] == ["matrix-entries"]
    assert by_id["MGL5-INF-0611"]["missing_information"] == ["reference-matrix"]
    assert by_id["MGL5-INF-0105"]["execution_status"] == "CRITERION_MET"
    assert by_id["MGL5-INF-0106"]["execution_status"] == "CRITERION_MET"
    assert by_id["MGL5-INF-0109"]["execution_status"] == "CRITERION_MET"
