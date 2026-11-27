from metagente_luna_s4.batch2 import run_all
from metagente_luna_s4.d01_batch import run_all as run_first


def test_second_batch_meets_the_stated_criteria():
    rows = run_all()
    assert len(rows) == 30
    assert {row["execution_status"] for row in rows} == {"CRITERION_MET"}
    by_id = {row["case_id"]: row["observed"] for row in rows}
    assert by_id["MGL5-INF-0101"] == {"sum": 15, "empty_sum": 0}
    assert by_id["MGL5-INF-0102"] == {"minimum": -8, "maximum": 19}
    assert by_id["MGL5-INF-0251"]["rejected"] == ["192.0.2.256"]
    assert by_id["MGL5-INF-0042"]["text"] == "0.10"
    assert by_id["MGL5-INF-0601"]["equal"] is False
    assert by_id["MGL5-INF-0052"]["detected"] == "elf"
    assert by_id["MGL5-INF-0052"]["extension_matches_content"] is False
    first = {row["case_id"] for row in run_first()}
    assert first.isdisjoint({row["case_id"] for row in rows})
    assert len(first) + len(rows) == 57
