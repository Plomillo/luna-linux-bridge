from __future__ import annotations

import importlib.util
from pathlib import Path

from metagente_luna_s3.registry import ORACLES, REGISTRY, run
from metagente_luna_s4.batch2 import CASES
from metagente_luna_s4.controls import run_controls

SCRIPT = Path(__file__).parents[1] / "scripts" / "build_c05_executable_plans.py"
SPEC = importlib.util.spec_from_file_location("build_c05_executable_plans", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
COMPILER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPILER)


EXPECTED = {
    "MGL5-INF-0070": "zip_path_safety",
    "MGL5-INF-0071": "zip_crc",
    "MGL5-INF-0072": "zip_duplicates",
    "MGL5-INF-0073": "tar_offsets",
    "MGL5-INF-0074": "tar_truncated",
    "MGL5-INF-0075": "gzip_crc",
    "MGL5-INF-0078": "sqlite_header",
    "MGL5-INF-0079": "sqlite_integrity",
    "MGL5-INF-0085": "wasm_header",
    "MGL5-INF-0080": "png_chunks",
    "MGL5-INF-0088": "unknown_format",
    "MGL5-INF-0089": "block_entropy",
    "MGL5-INF-0090": "binary_diff",
    "MGL5-INF-0097": "bounded_declared_size",
    "MGL5-INF-0099": "reproducible_structure",
}


def test_archive_forensics_source_cases_have_three_stable_oracled_runs():
    selected = {row["case_id"]: row for row in CASES if row["case_id"] in EXPECTED}
    assert set(selected) == set(EXPECTED)

    for case_id, capability in EXPECTED.items():
        spec = selected[case_id]
        observations = [run(capability, spec["arguments"]) for _ in range(3)]
        oracle = ORACLES[REGISTRY[capability].oracle_id]
        assert observations[0] == observations[1] == observations[2], case_id
        assert all(oracle(spec["arguments"], observed)["ok"] is True for observed in observations), case_id


def test_archive_forensics_cases_compile_with_source_and_two_controls():
    plans, _ = COMPILER.compile_plans()
    by_id = {plan["CASE_ID"]: plan for plan in plans}
    controls = {row["case_id"]: row for row in run_controls()}

    for case_id in EXPECTED:
        assert case_id in by_id
        assert case_id in by_id[case_id]["source_excerpt"]
        assert by_id[case_id]["source_metadata"]["excerpt_sha256"]
        assert set(controls[case_id]["controls"]) == {"negative", "boundary"}
        assert controls[case_id]["controls"]["negative"]["accepted"] is True
        assert controls[case_id]["controls"]["boundary"]["accepted"] is True
        assert controls[case_id]["controls"]["negative"]["run_kind"] == "NEGATIVE"
        assert controls[case_id]["controls"]["boundary"]["run_kind"] == "BOUNDARY"
        assert controls[case_id]["controls"]["negative"]["control_metadata"]["source"].endswith(f"{case_id}:negative")


def test_archive_forensics_capabilities_reject_untyped_extra_arguments():
    for capability in EXPECTED.values():
        schema = REGISTRY[capability].input_schema
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
