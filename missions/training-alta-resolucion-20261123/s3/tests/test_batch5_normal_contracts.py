from metagente_luna_s4.batch5 import CASES
from metagente_luna_s4.runner import execute
from metagente_luna_s4.controls import run_controls


EXPECTED = {
    "MGL5-INF-0113": ("balanced_range", "range_sum"),
    "MGL5-INF-0119": ("linear_scans", "full_scans"),
    "MGL5-INF-0141": ("parameterized_name", "own_query"),
    "MGL5-INF-0154": ("precedence_tree", "folded_value"),
    "MGL5-INF-0186": ("divide_zero", "zero_type"),
    "MGL5-INF-0208": ("mode_0640", "octal_mode"),
    "MGL5-INF-0209": ("umask_0027", "masked_create"),
    "MGL5-INF-0233": ("child_env", "declared_env"),
    "MGL5-INF-0308": ("reject_age", "own_check"),
    "MGL5-INF-0503": ("exit_codes", "posix_codes"),
}


def test_ten_source_defined_batch5_normal_operations_match_independent_oracles():
    by_id = {case["case_id"]: case for case in CASES}
    assert set(EXPECTED).issubset(by_id)

    for case_id, (capability, oracle_method) in EXPECTED.items():
        spec = by_id[case_id]
        assert spec["capability_id"] == capability
        assert spec["arguments"] == {}

        runs = [
            execute(spec["capability_id"], spec["arguments"], case_id)
            for _ in range(3)
        ]
        assert all(run["execution_status"] == "EXECUTED" for run in runs), case_id
        assert all(run["oracle_result"] and run["oracle_result"].get("ok") is True for run in runs), case_id
        assert all(run["oracle_result"].get("method") for run in runs), case_id
        assert all(run["observed"] == runs[0]["observed"] for run in runs), case_id
        assert all(run["oracle_result"]["method"] == runs[0]["oracle_result"]["method"] for run in runs), case_id
        assert oracle_method in {
            "range_sum", "full_scans", "own_query", "folded_value", "zero_type",
            "octal_mode", "masked_create", "declared_env", "own_check", "posix_codes",
        }


def test_source_defined_batch5_normal_specs_do_not_claim_negative_or_boundary_coverage():
    by_id = {case["case_id"]: case for case in CASES}
    for case_id in EXPECTED:
        assert by_id[case_id]["arguments"] == {}
    # Normal fixtures remain source-defined and deliberately separate from controls.



def test_ten_batch5_cases_have_distinct_accepted_negative_and_boundary_controls():
    expected = {
        "MGL5-INF-0113", "MGL5-INF-0119", "MGL5-INF-0141", "MGL5-INF-0154",
        "MGL5-INF-0186", "MGL5-INF-0208", "MGL5-INF-0209", "MGL5-INF-0233",
        "MGL5-INF-0308", "MGL5-INF-0503",
    }
    rows = {row["case_id"]: row for row in run_controls()}
    assert expected.issubset(rows)
    for case_id in expected:
        controls = rows[case_id]["controls"]
        assert set(controls) == {"negative", "boundary"}, case_id
        assert controls["negative"]["accepted"] is True, (case_id, controls["negative"])
        assert controls["boundary"]["accepted"] is True, (case_id, controls["boundary"])
