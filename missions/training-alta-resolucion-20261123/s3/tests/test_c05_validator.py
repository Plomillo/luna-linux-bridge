from metagente_luna_s4.c05_validator import contradictions, validate
from metagente_luna_s4.reconcile import amendments, intersection, manifest


def test_population_intersection_is_exact():
    report = intersection()
    assert report["helper_records"] == 106
    assert report["helper_criterion_met"] == 103
    assert report["helper_blocked"] == 3
    assert report["met_inside_m0_fail"] == 83
    assert report["met_inside_m0_pass"] == 20
    assert report["blocked_inside_m0_fail"] == 3
    assert report["m0_fail_without_helper"] == 894
    assert report["identity"] == "83 + 3 + 894 = 980"
    assert report["contractual_pass"] == 0


def test_withdrawn_claims_stay_out_of_contractual_pass():
    by_id = {row["CASE_ID"]: row for row in amendments()}
    assert len(by_id) == 106
    for case_id in ("MGL5-INF-0106", "MGL5-INF-0109", "MGL5-INF-0632"):
        assert by_id[case_id]["S4_HELPER_RESULT"] == "CRITERION_MET"
        assert by_id[case_id]["HELPER_DISPOSITION"] == "WITHDRAWN"
        assert by_id[case_id]["CONTRACTUAL_RESULT"] == "BLOCKED"
        assert by_id[case_id]["ROOT_CAUSE"]


def test_validator_rejects_a_promoted_helper_and_does_not_pass_c05():
    promoted = {"CASE_ID": "MGL5-INF-0001", "contract_status": "PASS", "basis": "CRITERION_MET", "run_ids": ["a", "a"]}
    assert "criterion-met-promoted-to-pass" in contradictions(promoted)
    assert "duplicate-run-id" in contradictions(promoted)
    historical = [{"CASE_ID": case_id, "execution_status": "NOT_RUN", "contract_status": "NOT_RUN"} for case_id in (f"MGL5-INF-{number:04d}" for number in range(1, 1001))]
    verdict = validate(historical)
    assert verdict["c05_passed"] is False
    assert verdict["c05_status"] == "NOT_PASSED"
    assert verdict["not_run"] == 1000
    assert verdict["human_review_required"] is False
    assert manifest()["c05_status"] == "NOT_PASSED"
    assert manifest()["global_condition_counter"] == "4/26"
