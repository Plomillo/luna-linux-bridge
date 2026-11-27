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
