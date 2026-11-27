from __future__ import annotations

from metagente_luna_s3.registry import ORACLES, run
from metagente_luna_s4.d01_batch import CASES


def test_new_d01_compatibility_cases_have_independent_oracle_passes():
    selected = {
        "MGL5-INF-0033", "MGL5-INF-0034", "MGL5-INF-0035",
        "MGL5-INF-0039", "MGL5-INF-0040", "MGL5-INF-0049",
    }
    specs = {row["case_id"]: row for row in CASES}
    assert selected <= set(specs)
    for case_id in sorted(selected):
        spec = specs[case_id]
        observed = run(spec["capability_id"], spec["arguments"])
        adjudication = ORACLES[spec["capability_id"]](spec["arguments"], observed)
        assert adjudication["ok"] is True, (case_id, observed, adjudication)


def test_parameterized_ieee754_cases_preserve_normal_and_edge_vectors():
    specs = {row["case_id"]: row for row in CASES}
    for case_id in ("MGL5-INF-0013", "MGL5-INF-0014", "MGL5-INF-0015"):
        spec = specs[case_id]
        observed = run(spec["capability_id"], spec["arguments"])
        assert ORACLES[spec["capability_id"]](spec["arguments"], observed)["ok"] is True
