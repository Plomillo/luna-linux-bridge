from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "build_c05_coverage_matrix.py"
SPEC = importlib.util.spec_from_file_location("build_c05_coverage_matrix", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
coverage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage)


def test_coverage_matrix_accounts_for_every_source_case_without_promoting_missing_plans():
    rows, summary = coverage.build()

    assert len(rows) == 1000
    assert [row["CASE_ID"] for row in rows] == [
        f"MGL5-INF-{number:04d}" for number in range(1, 1001)
    ]
    assert summary["counts"]["source_defined"] == 1000
    assert summary["counts"]["normal_spec_defined"] == 152
    assert summary["counts"]["ready_for_execution"] == 152
    assert summary["counts"]["blocked"] == 848
    assert summary["counts"]["interpreter_candidates"] == 7
    assert summary["counts"]["interpreter_ready"] == 2
    assert summary["counts"]["interpreter_blocked"] == 5
    assert summary["counts"]["interpreter_registered"] == 2
    assert summary["counts"]["no_normal_spec_and_no_interpreter_candidate"] == 844
    assert summary["counts"]["normal_spec_incomplete"] == 0
    assert summary["certification"] == "NOT_PASSED"


def test_coverage_matrix_identifies_missing_plan_and_control_reasons():
    rows, summary = coverage.build()
    by_id = {row["CASE_ID"]: row for row in rows}

    assert by_id["MGL5-INF-0001"]["ready_for_execution"] is True
    assert by_id["MGL5-INF-0006"]["ready_for_execution"] is True
    assert by_id["MGL5-INF-0054"]["ready_for_execution"] is True
    assert by_id["MGL5-INF-0055"]["ready_for_execution"] is True
    assert "NORMAL_EXECUTION_SPEC_MISSING" not in by_id["MGL5-INF-0054"]["blockers"]
    assert by_id["MGL5-INF-0103"]["ready_for_execution"] is True
    assert by_id["MGL5-INF-0107"]["ready_for_execution"] is True
    assert by_id["MGL5-INF-0108"]["ready_for_execution"] is True
    assert by_id["MGL5-INF-0104"]["ready_for_execution"] is True
    assert by_id["MGL5-INF-0105"]["ready_for_execution"] is True
    assert by_id["MGL5-INF-0109"]["ready_for_execution"] is True
    assert by_id["MGL5-INF-0106"]["interpreter_status"] == "BLOCKED"
    assert by_id["MGL5-INF-0106"]["ready_for_execution"] is True
    assert "INTERPRETER_CANDIDATE_NOT_READY" not in by_id["MGL5-INF-0106"]["blockers"]
    assert summary["blocker_counts"]["NORMAL_EXECUTION_SPEC_MISSING"] == 848


def test_require_complete_gate_fails_closed_for_incomplete_population(monkeypatch):
    monkeypatch.setattr("sys.argv", ["build_c05_coverage_matrix.py", "--require-complete"])
    assert coverage.main() == 1
