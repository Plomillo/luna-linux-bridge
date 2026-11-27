"""Fifth batch. These identifiers were not executed before."""
from __future__ import annotations

import json
from pathlib import Path

from metagente_luna_s4.runner import execute

PARAMS = json.loads((Path(__file__).resolve().parents[2] / "fixtures" / "derived_parameters.json").read_text(encoding="utf-8"))

CASES = [
    {"case_id": "MGL5-INF-0103", "capability_id": "first_match", "arguments": {"needle": 7, "values": [2, 7, 9, 7]}},
    {"case_id": "MGL5-INF-0104", "capability_id": "binary_find", "arguments": {"needle": 13, "start": 1, "end": 31}},
    {"case_id": "MGL5-INF-0110", "capability_id": "dequeue_named", "arguments": {"values": ["A", "B", "C"]}},
    {"case_id": "MGL5-INF-0113", "capability_id": "balanced_range", "arguments": {"count": 1000}},
    {"case_id": "MGL5-INF-0119", "capability_id": "linear_scans", "arguments": {"sizes": [1000, 2000, 4000]}},
    {"case_id": "MGL5-INF-0120", "capability_id": "factorials", "arguments": {"values": list(range(13))}},
    {"case_id": "MGL5-INF-0154", "capability_id": "precedence_tree", "arguments": {"expression": "1+2*3-4"}},
    {"case_id": "MGL5-INF-0171", "capability_id": "index_limit", "arguments": {"length": 8}},
    {"case_id": "MGL5-INF-0186", "capability_id": "divide_zero", "arguments": {"numerator": 1, "denominator": 0}},
    {"case_id": "MGL5-INF-0208", "capability_id": "mode_0640", "arguments": {"mode": 416}},
    {"case_id": "MGL5-INF-0209", "capability_id": "umask_0027", "arguments": {"umask": 23, "requested_mode": 438}},
    {"case_id": "MGL5-INF-0233", "capability_id": "child_env", "arguments": {"env_key": "test", "env_value": "123"}},
    {"case_id": "MGL5-INF-0252", "capability_id": "expand_v6", "arguments": {"address": "2001:db8::1"}},
    {"case_id": "MGL5-INF-0256", "capability_id": "mask_bits", "arguments": {"mask": "255.0.255.0"}},
    {"case_id": "MGL5-INF-0308", "capability_id": "reject_age", "arguments": {"age": -4, "minimum_age": 0}},
    {"case_id": "MGL5-INF-0141", "capability_id": "parameterized_name", "arguments": {"payload": "' OR 1=1 --", "stored_name": "ada"}},
    {"case_id": "MGL5-INF-0503", "capability_id": "exit_codes", "arguments": {"commands": ["true", "false", "luna-command-absent"]}},
    {"case_id": "MGL5-INF-0602", "capability_id": "sqrt_two", "arguments": {"value": 2.0}},
    {"case_id": "MGL5-INF-0607", "capability_id": "compensated_sum", "arguments": {"start": 1.0, "increment": 1e-8, "count": 100000}},
    {"case_id": "MGL5-INF-0616", "capability_id": "newton_root", "arguments": {"initial": 1.0, "target": 2.0}},
    {"case_id": "MGL5-INF-0618", "capability_id": "bracket_cube", "arguments": {"low": PARAMS["cube-interval"]["low"], "high": PARAMS["cube-interval"]["high"]}},
    {"case_id": "MGL5-INF-0623", "capability_id": "two_variances", "arguments": {"values": [2, 4, 4, 4, 5, 5, 7, 9]}},
    {"case_id": "MGL5-INF-0629", "capability_id": "exact_line", "arguments": {"xs": PARAMS["line-points"]["xs"], "slope": PARAMS["line-points"]["slope"], "intercept": PARAMS["line-points"]["intercept"]}},
    {"case_id": "MGL5-INF-0638", "capability_id": "euler_decay", "arguments": {"coarse_step": PARAMS["euler-steps"]["coarse_step"], "fine_step": PARAMS["euler-steps"]["fine_step"]}},
    {"case_id": "MGL5-INF-0639", "capability_id": "rk4_decay", "arguments": {"step": PARAMS["rk4-step"]["step"]}},
]


def run_all() -> list[dict]:
    rows = []
    for spec in CASES:
        runs = [execute(spec["capability_id"], spec["arguments"], spec["case_id"]) for _ in range(3)]
        observed = [run["observed"] for run in runs]
        stable = all(item == observed[0] for item in observed)
        ok = all(run["execution_status"] == "EXECUTED" for run in runs) and stable
        rows.append({
            "case_id": spec["case_id"],
            "observed": observed[0],
            "execution_status": "CRITERION_MET" if ok else runs[0]["execution_status"],
            "stderr": runs[0]["stderr"],
            "repetitions": [run["run_id"] for run in runs],
            "backend": "LOCAL_TEST_ONLY",
            "c05_gate": "NOT_PASSED",
        })
    return rows
