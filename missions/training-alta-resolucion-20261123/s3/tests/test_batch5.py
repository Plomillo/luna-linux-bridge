from metagente_luna_s4.batch5 import run_all


def test_fifth_batch_executes_the_literal_cases():
    rows = run_all()
    assert len(rows) == 25
    failed = [row for row in rows if row["execution_status"] != "CRITERION_MET"]
    assert failed == []
    by_id = {row["case_id"]: row["observed"] for row in rows}
    assert by_id["MGL5-INF-0103"]["index"] == 1
    assert by_id["MGL5-INF-0104"]["index"] == 12
    assert by_id["MGL5-INF-0110"]["dequeued"] == ["A", "B", "C"]
    assert by_id["MGL5-INF-0120"]["values"][0] == 1
    assert by_id["MGL5-INF-0120"]["values"][5] == 120
    assert by_id["MGL5-INF-0154"]["value"] == 3
    assert by_id["MGL5-INF-0186"]["type"] == "ZeroDivisionError"
    assert by_id["MGL5-INF-0208"]["mode"] == 0o640
    assert by_id["MGL5-INF-0252"]["expanded"] == "2001:0db8:0000:0000:0000:0000:0000:0001"
    assert by_id["MGL5-INF-0308"]["rejected"] is True
    assert by_id["MGL5-INF-0141"]["matched"] == 0
    assert by_id["MGL5-INF-0503"]["codes"] == [0, 1, 127]
    assert by_id["MGL5-INF-0623"]["population"] == 4
