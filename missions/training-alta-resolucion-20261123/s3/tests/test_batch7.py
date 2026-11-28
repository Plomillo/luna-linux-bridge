from metagente_luna_s3.batch7_exec import trend_stationarity
from metagente_luna_s3.batch7_oracle import trend_stationarity_oracle
from metagente_luna_s4.controls import accepts
from metagente_luna_s4.independent_validator import _independent_control_accepts


def test_inf0634_source_fixture_detects_deterministic_linear_trend_with_fixed_oracle():
    arguments = {"values": [1, 2, 3, 4, 5, 6, 7, 8]}
    runs = [trend_stationarity(arguments["values"]) for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]
    assert runs[0]["status"] == "TREND_EVIDENCE"
    assert runs[0]["slope"] == 1.0
    assert runs[0]["r_squared"] == 1.0
    assert "not a formal stationarity hypothesis test" in runs[0]["limitation"]
    assert trend_stationarity_oracle(arguments, runs[0])["ok"] is True


def test_inf0634_negative_control_does_not_overclaim_trend_and_both_adjudicators_accept():
    arguments = {"values": [2, 4, 3, 4, 3, 2, 4, 3]}
    observed = trend_stationarity(arguments["values"])
    expect = "trend-no-evidence"
    assert observed["status"] == "NO_TREND_EVIDENCE"
    assert trend_stationarity_oracle(arguments, observed)["ok"] is True
    assert accepts(expect, observed, "EXECUTED") is True
    assert _independent_control_accepts(expect, observed, "EXECUTED") is True
    assert accepts(expect, observed, "BLOCKED") is False
    assert _independent_control_accepts(expect, observed, "BLOCKED") is False


def test_inf0634_two_observation_boundary_declares_insufficient_power():
    arguments = {"values": [1, 2]}
    observed = trend_stationarity(arguments["values"])
    expect = "trend-insufficient-power"
    assert observed["status"] == "INSUFFICIENT_POWER"
    assert observed["slope"] is None and observed["r_squared"] is None
    assert trend_stationarity_oracle(arguments, observed)["ok"] is True
    assert accepts(expect, observed, "EXECUTED") is True
    assert _independent_control_accepts(expect, observed, "EXECUTED") is True


def test_inf0634_constant_series_is_not_misclassified_as_trend():
    arguments = {"values": [5, 5, 5, 5]}
    observed = trend_stationarity(arguments["values"])
    assert observed["status"] == "NO_VARIATION"
    assert trend_stationarity_oracle(arguments, observed)["ok"] is True
