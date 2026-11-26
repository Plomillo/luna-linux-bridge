import os

from metagente_luna_s4.controls import run_controls
from metagente_luna_s4.isolated import execute_isolated, run_bounded


def test_process_separation_hides_secrets_and_times_out(monkeypatch):
    monkeypatch.setenv("LUNA_SECRET", "do-not-leak")
    outcome = run_bounded("import os; print(os.environ.get('LUNA_SECRET'))", "", 2)
    assert outcome["status"] == "FINISHED"
    assert "do-not-leak" not in outcome["stdout"]
    timed = run_bounded("import time; time.sleep(5)", "", 0.2)
    assert timed["status"] == "TIMEOUT"
    assert os.environ["LUNA_SECRET"] == "do-not-leak"


def test_isolated_case_matches_the_known_sum():
    record = execute_isolated("array_sum", {"values": [-3, 0, 7, 11], "empty": []}, "MGL5-INF-0101")
    assert record["backend"] == "PROCESS_SEPARATION"
    assert record["sandbox"] is False
    assert record["observed"] == {"sum": 15, "empty_sum": 0}
    assert record["execution_status"] == "EXECUTED"


def test_controls_that_were_defined_are_accepted():
    rows = run_controls()
    defined = [row for row in rows if row["controls"]]
    assert defined
    assert all(row["control_status"] == "PRESENT" for row in defined)
    assert len(defined) >= 30
