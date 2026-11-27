from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "execute_c05_population.py"
SPEC = importlib.util.spec_from_file_location("execute_c05_population", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
population = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(population)


def test_population_plan_forwards_pinned_docker_image_to_all_five_runs(monkeypatch, tmp_path):
    image_id = "sha256:" + "a" * 64
    observed_images = []

    def fake_execute_isolated(
        capability_id,
        arguments,
        case_id,
        *,
        evidence_root,
        run_kind,
        control_metadata=None,
        source_metadata=None,
        source_excerpt=None,
        timeout_seconds=60,
        sandbox_image=None,
    ):
        observed_images.append(sandbox_image)
        run_number = len(observed_images)
        return {
            "case_id": case_id,
            "run_kind": run_kind,
            "persisted_evidence": {
                "case_id": case_id,
                "run_id": f"run-{run_number:08d}",
                "started": 1.0,
                "ended": 2.0,
                "artifacts": {},
                "clean_state": True,
                "execution_status": "PASS",
                "exit_code": 0,
            },
        }

    monkeypatch.setattr(population, "execute_isolated", fake_execute_isolated)
    monkeypatch.setattr(population, "independently_validate_case", lambda row, root: {"passed": True})

    plan = {
        "source_metadata": {"source_file": "source.txt"},
        "source_excerpt": "MGL5-INF-0001 source excerpt",
        "normal": {"capability_id": "cap", "arguments": {}},
        "negative": {
            "capability_id": "cap",
            "arguments": {},
            "control_metadata": {
                "definition": "negative input",
                "expected_behavior": "rejected",
                "source": "case criterion",
            },
        },
        "boundary": {
            "capability_id": "cap",
            "arguments": {},
            "control_metadata": {
                "definition": "boundary input",
                "expected_behavior": "accepted at boundary",
                "source": "case criterion",
            },
        },
    }

    row = population.execute_plan(plan, "MGL5-INF-0001", tmp_path, 30, image_id)

    assert len(observed_images) == 5
    assert observed_images == [image_id] * 5
    assert len(row["repetitions"]) == 3
    assert {item["kind"] for item in row["controls"]} == {"NEGATIVE", "BOUNDARY"}


def test_population_cli_rejects_mutable_or_unpinned_image_reference(capsys):
    result = population.main([
        "execute_c05_population.py",
        "dossiers.jsonl",
        "plans.jsonl",
        "evidence",
        "ledger.jsonl",
        "report.json",
        "python:3.12-slim",
    ])

    assert result == 2
    assert "immutable" in capsys.readouterr().err



def test_plan_compiler_emits_only_cases_with_both_authored_controls():
    script = Path(__file__).parents[1] / "scripts" / "build_c05_executable_plans.py"
    compiler_spec = importlib.util.spec_from_file_location("build_c05_executable_plans", script)
    assert compiler_spec is not None and compiler_spec.loader is not None
    compiler = importlib.util.module_from_spec(compiler_spec)
    compiler_spec.loader.exec_module(compiler)

    plans, report = compiler.compile_plans()

    assert report["compiled_executable_plans"] == len(plans) == 15
    assert report["not_in_plan_set"] == 985
    assert report["certification"] == "NOT_PASSED"
    assert [plan["CASE_ID"] for plan in plans] == sorted(plan["CASE_ID"] for plan in plans)
    for plan in plans:
        assert plan["source_metadata"]["source_blob"]
        assert plan["source_metadata"]["excerpt_sha256"]
        assert plan["source_metadata"]["operation"] in plan["source_excerpt"]
        assert plan["source_metadata"]["acceptance_criterion"] in plan["source_excerpt"]
        assert plan["source_metadata"]["oracle_requirement"] in plan["source_excerpt"]
        assert plan["negative"]["control_metadata"]["expect"]
        assert plan["boundary"]["control_metadata"]["expect"]
        assert plan["normal"]["arguments"] != plan["negative"]["arguments"]
        assert plan["normal"]["arguments"] != plan["boundary"]["arguments"]
        assert plan["negative"]["arguments"] != plan["boundary"]["arguments"]


def test_population_plan_requires_machine_checkable_control_expectations():
    plan = {
        "source_metadata": {},
        "source_excerpt": "",
        "normal": {"capability_id": "cidr_bounds", "arguments": {"cidr": "192.0.2.130/26"}},
        "negative": {
            "capability_id": "cidr_bounds",
            "arguments": {"cidr": "192.0.2.130/33"},
            "control_metadata": {
                "definition": "invalid prefix",
                "expected_behavior": "reject",
                "source": "source case",
            },
        },
        "boundary": {
            "capability_id": "cidr_bounds",
            "arguments": {"cidr": "192.0.2.130/32"},
            "control_metadata": {
                "definition": "host prefix",
                "expected_behavior": "accept",
                "source": "source case",
                "expect": "boundary-accepted",
            },
        },
    }

    errors = population.plan_errors(plan, "MGL5-INF-0001")

    assert "negative-control-definition-incomplete" in errors


def test_compiled_plans_pass_source_and_capability_preflight():
    script = Path(__file__).parents[1] / "scripts" / "build_c05_executable_plans.py"
    compiler_spec = importlib.util.spec_from_file_location("build_c05_executable_plans_preflight", script)
    assert compiler_spec is not None and compiler_spec.loader is not None
    compiler = importlib.util.module_from_spec(compiler_spec)
    compiler_spec.loader.exec_module(compiler)
    plans, _ = compiler.compile_plans()

    for plan in plans:
        assert population.plan_errors(plan, plan["CASE_ID"]) == []

def test_complete_blocked_population_is_evidence_complete_but_not_c05_certified():
    report = {
        "expected": 1000,
        "rows": 1000,
        "authentic_results": 1000,
        "not_run": 0,
        "rejected": [],
        "c05_passed": False,
        "c05_status": "NOT_PASSED",
        "execution_outcomes": {"BLOCKED": 985, "PASS": 15, "FAIL": 0, "INCONCLUSIVE": 0},
    }

    assert population.evidence_population_complete(report) is True
    assert report["c05_passed"] is False
    assert report["c05_status"] == "NOT_PASSED"


def test_incomplete_or_rejected_population_is_not_evidence_complete():
    report = {
        "expected": 1000,
        "rows": 1000,
        "authentic_results": 999,
        "not_run": 1,
        "rejected": [{"case_id": "MGL5-INF-1000"}],
    }

    assert population.evidence_population_complete(report) is False
