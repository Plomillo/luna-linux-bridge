from __future__ import annotations

from metagente_luna_s3.registry import EXECUTORS, ORACLES
from metagente_luna_s4.controls import CONTROLS, _build, accepts
from metagente_luna_s4.d03_batch import CASES
from metagente_luna_s4.runner import execute


def test_d03_normal_plans_match_independent_oracles_three_times():
    for spec in CASES:
        runs = [
            execute(spec["capability_id"], spec["arguments"], spec["case_id"])
            for _ in range(3)
        ]
        assert all(row["execution_status"] == "EXECUTED" for row in runs), (spec["case_id"], runs)
        assert runs[0]["observed"] == runs[1]["observed"] == runs[2]["observed"]
        assert all(row["oracle_result"]["ok"] is True for row in runs)


def test_d03_negative_and_boundary_controls_are_distinct_and_adjudicated():
    _build()
    for spec in CASES:
        controls = CONTROLS[spec["case_id"]]
        assert set(controls) == {"negative", "boundary"}
        assert controls["negative"]["arguments"] != controls["boundary"]["arguments"]
        for kind, item in controls.items():
            result = execute(
                item["capability_id"], item["arguments"], spec["case_id"],
                run_kind=kind.upper(),
                control_metadata={
                    "definition": f"{kind} control {item['expect']}",
                    "expected_behavior": f"accepts({item['expect']!r}, observed, lifecycle_status)",
                    "source": f"d03_batch.py:{spec['case_id']}:{kind}",
                },
            )
            assert result["execution_status"] in {"EXECUTED", "FAIL"}
            assert accepts(item["expect"], result["observed"], result["lifecycle_status"]), (
                spec["case_id"], kind, result
            )


def test_d03_registry_has_distinct_producer_and_oracle_modules():
    for spec in CASES:
        capability = spec["capability_id"]
        assert capability in EXECUTORS
        assert capability in ORACLES
        assert EXECUTORS[capability].__module__ != ORACLES[capability].__module__
