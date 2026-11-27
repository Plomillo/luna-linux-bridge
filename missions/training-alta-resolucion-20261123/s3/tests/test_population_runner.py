from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "execute_c05_population.py"
SPEC = importlib.util.spec_from_file_location("execute_c05_population", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
population = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(population)


def test_valid_plans_execute_concurrently_with_deterministic_result_order(monkeypatch, tmp_path):
    from threading import Barrier

    barrier = Barrier(2)

    def fake_execute_plan(plan, case_id, evidence_root, timeout, image):
        barrier.wait(timeout=3)
        return {"CASE_ID": case_id, "execution_status": "PASS"}

    monkeypatch.setattr(population, "execute_plan", fake_execute_plan)
    plans = {
        "MGL5-INF-0001": {"normal": {}},
        "MGL5-INF-0002": {"normal": {}},
    }
    results = population.execute_valid_plans(
        plans, set(plans), tmp_path, "sha256:" + "a" * 64, max_workers=2,
    )
    assert list(results) == ["MGL5-INF-0001", "MGL5-INF-0002"]
    assert all(row["execution_status"] == "PASS" for row in results.values())


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
                "expect": "different-text",
            },
        },
        "boundary": {
            "capability_id": "cap",
            "arguments": {},
            "control_metadata": {
                "definition": "boundary input",
                "expected_behavior": "accepted at boundary",
                "source": "case criterion",
                "expect": "empty-roundtrip",
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

    assert report["compiled_executable_plans"] == len(plans) == 86
    assert report["not_in_plan_set"] == 914
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

def _compiled_case_ids():
    script = Path(__file__).parents[1] / "scripts" / "build_c05_executable_plans.py"
    compiler_spec = importlib.util.spec_from_file_location("build_c05_executable_plans_inventory", script)
    assert compiler_spec is not None and compiler_spec.loader is not None
    compiler = importlib.util.module_from_spec(compiler_spec)
    compiler_spec.loader.exec_module(compiler)
    plans, _ = compiler.compile_plans()
    return {plan["CASE_ID"] for plan in plans}


def test_86_authored_plans_and_914_explicit_not_run_complete_inventory_not_c05():
    executable = _compiled_case_ids()
    rejected = [case_id for case_id in population.EXPECTED if case_id not in executable]
    report = {
        "expected": 1000,
        "rows": 1000,
        "authentic_results": len(executable),
        "not_run": len(rejected),
        "rejected": [{"case_id": case_id, "reasons": ["case-not-executed"]} for case_id in rejected],
        "c05_passed": False,
        "c05_status": "NOT_PASSED",
    }

    assert len(executable) == 86
    assert len(rejected) == 914
    assert population.evidence_inventory_complete(report, executable) is True
    assert report["c05_passed"] is False
    assert report["c05_status"] == "NOT_PASSED"


def test_inventory_gate_rejects_missing_or_fabricated_execution_evidence():
    report = {
        "expected": 1000,
        "rows": 1000,
        "authentic_results": 1000,
        "not_run": 0,
        "rejected": [],
    }

    assert population.evidence_inventory_complete(report, _compiled_case_ids()) is False

def test_inventory_gate_rejects_duplicate_or_noncanonical_blocker_ids():
    executable = _compiled_case_ids()
    rejected = [case_id for case_id in population.EXPECTED if case_id not in executable]
    report = {
        "expected": 1000,
        "rows": 1000,
        "authentic_results": len(executable),
        "not_run": len(rejected),
        "rejected": [
            {"case_id": case_id, "reasons": ["case-not-executed"]}
            for case_id in rejected
        ],
    }
    report["rejected"][-1]["case_id"] = report["rejected"][0]["case_id"]

    assert population.evidence_inventory_complete(report, executable) is False


def test_inventory_gate_rejects_blocker_set_that_is_not_exact_executable_complement():
    executable = _compiled_case_ids()
    rejected_ids = [case_id for case_id in population.EXPECTED if case_id not in executable]
    rejected_ids[-1] = min(executable)  # omit a genuine NOT_RUN case and misclassify an executable case
    report = {
        "expected": 1000,
        "rows": 1000,
        "authentic_results": len(executable),
        "not_run": len(rejected_ids),
        "rejected": [
            {"case_id": case_id, "reasons": ["case-not-executed"]}
            for case_id in rejected_ids
        ],
    }
    assert population.evidence_inventory_complete(report, executable) is False


def test_population_refuses_preexisting_blocker_output_before_any_execution(tmp_path, capsys):
    dossiers = tmp_path / "dossiers.jsonl"
    plans = tmp_path / "plans.jsonl"
    evidence = tmp_path / "evidence"
    ledger = tmp_path / "ledger.jsonl"
    report = tmp_path / "report.json"
    blockers = tmp_path / "C05_POPULATION_BLOCKERS.jsonl"
    dossiers.write_text(
        "".join(json.dumps({"CASE_ID": case_id}) + "\n" for case_id in population.EXPECTED),
        encoding="utf-8",
    )
    plans.write_text("", encoding="utf-8")
    blockers.write_text("historical evidence", encoding="utf-8")

    result = population.main([
        "execute_c05_population.py",
        str(dossiers),
        str(plans),
        str(evidence),
        str(ledger),
        str(report),
        "sha256:" + "a" * 64,
    ])

    assert result == 2
    assert "refusing to overwrite historical evidence" in capsys.readouterr().err
    assert not ledger.exists()
    assert not report.exists()
    assert blockers.read_text(encoding="utf-8") == "historical evidence"

def test_contract_adjudication_requires_three_normal_passes_and_both_control_expectations():
    plan = {
        "negative": {"control_metadata": {"expect": "different-text"}},
        "boundary": {"control_metadata": {"expect": "empty-roundtrip"}},
    }
    normal = [
        {
            "execution_status": "PASS",
            "lifecycle_status": "EXECUTED",
            "oracle_result": {"ok": True},
        }
        for _ in range(3)
    ]
    negative = {
        "execution_status": "PASS",
        "lifecycle_status": "EXECUTED",
        "observed": {"recovered": "Luna-2025"},
    }
    boundary = {
        "execution_status": "PASS",
        "lifecycle_status": "EXECUTED",
        "observed": {"recovered": ""},
    }

    accepted = population.evaluate_contract(plan, normal + [negative, boundary])
    assert accepted["normal_repetitions_pass"] is True
    assert accepted["controls_pass"] is True

    rejected = population.evaluate_contract(
        plan,
        normal + [{**negative, "observed": {"recovered": "Luna-2026"}}, boundary],
    )
    assert rejected["controls_pass"] is False


def test_contract_adjudication_rejects_any_nonpassing_normal_repetition():
    plan = {
        "negative": {"control_metadata": {"expect": "different-text"}},
        "boundary": {"control_metadata": {"expect": "empty-roundtrip"}},
    }
    normal = [
        {"execution_status": "PASS", "lifecycle_status": "EXECUTED", "oracle_result": {"ok": True}}
        for _ in range(3)
    ]
    normal[1]["execution_status"] = "FAIL"
    runs = normal + [
        {"execution_status": "PASS", "lifecycle_status": "EXECUTED", "observed": {"recovered": "Luna-2025"}},
        {"execution_status": "PASS", "lifecycle_status": "EXECUTED", "observed": {"recovered": ""}},
    ]

    result = population.evaluate_contract(plan, runs)
    assert result["normal_repetitions_pass"] is False
