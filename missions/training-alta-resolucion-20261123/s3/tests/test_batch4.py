from metagente_luna_s3.batch4_exec import confined
from metagente_luna_s4.batch4 import run_all


def test_fourth_batch_meets_the_stated_results():
    rows = run_all()
    assert len(rows) == 9
    assert {row["execution_status"] for row in rows} == {"CRITERION_MET"}
    by_id = {row["case_id"]: row["observed"] for row in rows}
    assert by_id["MGL5-INF-0142"]["blocked"] is True
    assert by_id["MGL5-INF-0142"]["bytes_read"] == 0
    assert by_id["MGL5-INF-0411"]["values"] == [1.0, 0.0, -1.0]
    assert by_id["MGL5-INF-0555"]["completed"] == 100
    assert by_id["MGL5-INF-0555"]["ids"] == list(range(100))
    assert by_id["MGL5-INF-0561"] == {"availability": 0.99, "successes": 99, "failures": 1, "total": 100}
    assert by_id["MGL5-INF-0620"]["method"] == "trapezoidal"
    assert by_id["MGL5-INF-0620"]["weights"] == [1, 2, 2, 2, 1]
    assert by_id["MGL5-INF-0621"]["method"] == "simpson"
    assert by_id["MGL5-INF-0621"]["weights"] == [1, 4, 2, 4, 1]
    assert abs(by_id["MGL5-INF-0626"]["value"] - 1) < 1e-9
    assert abs(by_id["MGL5-INF-0627"]["value"] + 1) < 1e-9
    assert by_id["MGL5-INF-0633"]["lags"][0] == 1
    assert len(by_id["MGL5-INF-0633"]["lags"]) == 4


def test_download_allows_an_inside_file_and_blocks_a_symlink():
    inside = confined("allowed.txt")
    assert inside["blocked"] is False
    assert inside["bytes_read"] == len(b"payload")
    escaped = confined("escape")
    assert escaped["blocked"] is True
    assert escaped["bytes_read"] == 0
