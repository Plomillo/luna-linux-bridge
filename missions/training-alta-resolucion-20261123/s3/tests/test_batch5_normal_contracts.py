EXPECTED = {
    "MGL5-INF-0113": ("avl_tree", "avl_tree_reference"),
    "MGL5-INF-0119": ("linear_search_complexity", "linear_search_complexity_reference"),
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
    from metagente_luna_s4.batch5 import CASES
    from metagente_luna_s4.runner import execute

    by_id = {case["case_id"]: case for case in CASES}
    assert set(EXPECTED).issubset(by_id)

    for case_id, (capability, oracle_method) in EXPECTED.items():
        spec = by_id[case_id]
        assert spec["capability_id"] == capability
        expected_arguments = {
            "MGL5-INF-0113": {"values": list(range(1, 1001))},
            "MGL5-INF-0119": {"sizes": [1000, 2000, 4000], "target": 4000},
        }
        if case_id in expected_arguments:
            assert spec["arguments"] == expected_arguments[case_id]
        else:
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
            "avl_tree_reference", "linear_search_complexity_reference", "own_query", "folded_value", "zero_type",
            "octal_mode", "masked_create", "declared_env", "own_check", "posix_codes",
        }


def test_source_defined_batch5_normal_specs_do_not_claim_negative_or_boundary_coverage():
    from metagente_luna_s4.batch5 import CASES

    by_id = {case["case_id"]: case for case in CASES}
    assert by_id["MGL5-INF-0113"]["arguments"] == {"values": list(range(1, 1001))}
    assert by_id["MGL5-INF-0119"]["arguments"] == {"sizes": [1000, 2000, 4000], "target": 4000}
    for case_id in set(EXPECTED) - {"MGL5-INF-0113", "MGL5-INF-0119"}:
        assert by_id[case_id]["arguments"] == {}
    # Normal fixtures remain source-defined and deliberately separate from controls.



def test_ten_batch5_cases_have_distinct_accepted_negative_and_boundary_controls():
    from metagente_luna_s4.controls import run_controls

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
