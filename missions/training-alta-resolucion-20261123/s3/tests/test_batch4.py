from metagente_luna_s3.batch4_exec import acf_series, confined, pearson, run_operation
from metagente_luna_s4.batch4 import run_all


def test_fourth_batch_meets_the_stated_results():
    rows = run_all()
    assert len(rows) == 9
    assert {row["execution_status"] for row in rows} == {"CRITERION_MET"}, [(row["case_id"], row["execution_status"], row.get("observed"), row.get("stderr")) for row in rows]
    by_id = {row["case_id"]: row["observed"] for row in rows}
    assert by_id["MGL5-INF-0142"]["blocked"] is True
    assert by_id["MGL5-INF-0142"]["bytes_read"] == 0
    assert by_id["MGL5-INF-0142"]["reason"] == "parent-segment"
    assert by_id["MGL5-INF-0411"]["values"] == [1.0, 0.0, -1.0]
    assert by_id["MGL5-INF-0555"]["completed"] == 100
    assert by_id["MGL5-INF-0555"]["ids"] == list(range(100))
    assert by_id["MGL5-INF-0561"]["statuses"].count(200) == 99
    assert by_id["MGL5-INF-0561"]["statuses"].count(500) == 1
    assert by_id["MGL5-INF-0620"]["method"] == "trapezoidal"
    assert by_id["MGL5-INF-0620"]["weights"] == [1, 2, 2, 2, 1]
    assert by_id["MGL5-INF-0621"]["method"] == "simpson"
    assert by_id["MGL5-INF-0621"]["weights"] == [1, 4, 2, 4, 1]
    assert abs(by_id["MGL5-INF-0626"]["value"] - 1) < 1e-9
    assert abs(by_id["MGL5-INF-0627"]["value"] + 1) < 1e-9
    assert by_id["MGL5-INF-0633"]["lags"][0] == 1
    assert len(by_id["MGL5-INF-0633"]["lags"]) == 4


def test_download_rules_do_not_open_an_outside_target():
    inside = confined("allowed.txt")
    assert inside["blocked"] is False and inside["bytes_read"] == len(b"payload")
    linked = confined("inside-link")
    assert linked["reason"] == "internal-link" and linked["bytes_read"] == len(b"payload")
    assert confined("escape")["reason"] == "symlink-escapes"
    assert confined("nest/out")["reason"] == "symlink-escapes"
    assert confined("/etc/passwd")["reason"] == "absolute-or-nul"
    assert confined("missing.txt")["reason"] == "missing"
    assert confined("escape")["bytes_read"] == 0


def test_failed_token_is_not_a_successful_operation():
    assert run_operation("bad")["ok"] is False
    assert pearson([1], [1])["error"] == "invalid-sample"
    assert pearson([1, 1], [2, 2])["error"] == "zero-variance"
    assert acf_series([1])["error"] == "too-short"
    assert acf_series([2, 2, 2])["error"] == "zero-variance"
    lags = acf_series([1, 2, 3, 4])["lags"]
    assert abs(lags[1] - 0.25) < 1e-9
    assert abs(lags[2] + 0.3) < 1e-9
    assert abs(lags[3] + 0.45) < 1e-9


def test_cosine_and_acf_oracles_cover_negative_and_boundary_inputs():
    from metagente_luna_s3.batch4_exec import acf_series, cosine_set
    from metagente_luna_s3.batch4_oracle import axis_cosines, lag_identity

    zero = {"pairs": [[[0, 0], [1, 0]]]}
    assert axis_cosines(zero, cosine_set(zero["pairs"]))["ok"] is True
    same = {"pairs": [[[3, 4], [3, 4]]]}
    assert axis_cosines(same, cosine_set(same["pairs"]))["ok"] is True
    constant = {"values": [5, 5, 5]}
    assert lag_identity(constant, acf_series(constant["values"]))["ok"] is True
    two = {"values": [1, 2]}
    assert lag_identity(two, acf_series(two["values"]))["ok"] is True
