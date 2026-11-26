import hashlib

from metagente_luna_s4.c05_validator import contradictions, validate
from metagente_luna_s4.reconcile import amendments, intersection, manifest


def _population(status: str, **extra) -> list[dict]:
    rows = []
    for number in range(1, 1001):
        row = {"CASE_ID": f"MGL5-INF-{number:04d}", "execution_status": status, "contract_status": status}
        row.update(extra)
        rows.append(row)
    return rows


def _with_evidence(status: str) -> list[dict]:
    rows = []
    for number in range(1, 1001):
        payload = f"{status}:{number}"
        rows.append({
            "CASE_ID": f"MGL5-INF-{number:04d}",
            "execution_status": status,
            "contract_status": status,
            "evidence_payload": payload,
            "evidence_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            "fixture_sha256": "f" * 64,
        })
    return rows


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


def test_investigation_flag_cannot_turn_not_run_into_c05():
    rows = _population("NOT_RUN", individual_investigation=True)
    verdict = validate(rows)
    assert verdict["c05_passed"] is False
    assert verdict["c05_status"] == "NOT_PASSED"
    assert verdict["not_run"] == 1000
    assert verdict["authentic_results"] == 0
    assert verdict["not_run_counts_as_execution"] is False
    assert verdict["rejected"][0]["reasons"] == ["investigation-is-not-execution"]
    assert len(verdict["rejected"]) == 1000


def test_fail_is_an_outcome_and_pass_is_not_required():
    verdict = validate(_with_evidence("FAIL"))
    assert verdict["c05_passed"] is True
    assert verdict["contractual_pass"] == 0
    assert verdict["not_run"] == 0
    assert verdict["authentic_results"] == 1000


def test_adversarial_populations_are_rejected():
    duplicated = _with_evidence("FAIL")
    duplicated[1]["CASE_ID"] = duplicated[0]["CASE_ID"]
    assert validate(duplicated)["c05_passed"] is False
    missing = _with_evidence("FAIL")[:-1]
    assert validate(missing)["structure_problems"][0]["missing"] == 1
    promoted = _with_evidence("FAIL")
    promoted[0]["contract_status"] = "PASS"
    promoted[0]["basis"] = "CRITERION_MET"
    promoted[0]["execution_status"] = "NOT_RUN"
    assert "criterion-met-promoted-to-pass" in contradictions(promoted[0])
    assert "not-run-promoted-to-pass" in contradictions(promoted[0])
    copied = {"execution_status": "FAIL", "contract_status": "FAIL", "run_ids": ["a", "a"], "repetitions_copied": True}
    assert "duplicate-run-id" in contradictions(copied)
    assert "copied-repetition" in contradictions(copied)
    broken = _with_evidence("PASS")
    broken[0]["evidence_sha256"] = "0" * 64
    broken[0]["fixture_sha256"] = ""
    broken[0]["oracle_mode"] = "same-implementation"
    broken[0]["evidence_missing"] = True
    broken[0]["machinery_claimed"] = "M0"
    broken[0]["machinery_observed"] = "S4"
    reasons = contradictions(broken[0])
    assert "incorrect-evidence-hash" in reasons
    assert "pass-without-fixture-hash" in reasons
    assert "circular-oracle" in reasons
    assert "missing-evidence" in reasons
    assert "false-machinery-identity" in reasons
    assert validate(broken)["c05_passed"] is False
    historical = _population("NOT_RUN")
    assert validate(historical)["c05_passed"] is False
    assert manifest()["c05_status"] == "NOT_PASSED"
    assert manifest()["global_condition_counter"] == "4/26"
