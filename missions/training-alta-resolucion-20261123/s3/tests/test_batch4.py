from metagente_luna_s4.batch4 import run_all


def test_fourth_batch_meets_the_stated_results():
    rows = run_all()
    assert len(rows) == 9
    assert {row["execution_status"] for row in rows} == {"CRITERION_MET"}
    by_id = {row["case_id"]: row["observed"] for row in rows}
    assert by_id["MGL5-INF-0142"]["blocked"] is True
    assert by_id["MGL5-INF-0411"]["values"] == [1.0, 0.0, -1.0]
    assert by_id["MGL5-INF-0555"]["value"] == 100
    assert by_id["MGL5-INF-0561"]["value"] == 0.99
    assert by_id["MGL5-INF-0620"]["value"] == 0.5
    assert abs(by_id["MGL5-INF-0626"]["value"] - 1) < 1e-9
    assert abs(by_id["MGL5-INF-0627"]["value"] + 1) < 1e-9
    assert by_id["MGL5-INF-0633"]["lag0"] == 1
