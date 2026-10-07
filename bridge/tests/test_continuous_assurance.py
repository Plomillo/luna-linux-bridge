"""Continuous G23/G24 assurance matrix tests; no certification or signer spoofing."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import continuous_assurance as assurance

PLAN=json.loads((ROOT/"ASSURANCE_MATRIX.json").read_text())
SHA="f"*40


def ref(evidence_id="ONE",workstream="TRUST_AND_CERTIFICATION",
        phase="INTAKE",role="G23",commit=SHA):
    return {"evidence_id":evidence_id,"workstream":workstream,
            "phase":phase,"role":role,"source_commit":commit,"sha256":"0"*64,
            "source":"CI_EXAMPLE_UNVERIFIED","claim":"READONLY_STATIC_CHECK",
            "status":"REFERENCED_UNAUTHENTICATED"}


class ContinuousAssuranceTests(unittest.TestCase):
    def test_complete_4x5x2_coverage_without_self_certification(self):
        report=assurance.evaluate(PLAN,SHA)
        self.assertEqual(report["workstream_count"],4)
        self.assertEqual(report["gate_slots"],40)
        self.assertEqual(report["gate_slots_without_evidence_ref"],40)
        self.assertFalse(report["actual_independent_signatures_verified"])
        self.assertFalse(report["certified"])
        self.assertEqual(report["release_status"],"HOLD_EXTERNAL_G23_G24_AND_SECOND_ORDER")
        self.assertEqual(len(report["life_cycle"]),5)

    def test_g23_and_g24_parallel_prechecks_with_ordered_decisions(self):
        report=assurance.evaluate(PLAN,SHA)
        self.assertEqual(report["parallel_prechecks"],
            ["G23_EVIDENCE_AND_INDEPENDENCE_REVIEW","G24_CRITERIA_AND_SCOPE_READINESS"])
        self.assertEqual(report["serial_decision_dependency"],"FAVORABLE_G23_BEFORE_G24")
        for phase in report["life_cycle"]:
            self.assertTrue(phase["g23_and_g24_included_in_every_workstream"])
            for row in phase["workstreams"]:
                self.assertEqual(row["g23"]["plan"],"DEFINED_AT_DESIGN")
                self.assertEqual(row["g24"]["decision"],"BLOCKED_UNTIL_FAVORABLE_INDEPENDENT_G23")
                self.assertFalse(row["can_operationally_activate"])

    def test_incomplete_lifecycle_denied(self):
        p=deepcopy(PLAN)
        p["lifecycle"].remove("INTEGRATION")
        with self.assertRaisesRegex(RuntimeError,"LIFECYCLE_PHASES"):
            assurance.validate_plan(p)

    def test_reordered_lifecycle_denied(self):
        p=deepcopy(PLAN)
        p["lifecycle"][0],p["lifecycle"][1]=p["lifecycle"][1],p["lifecycle"][0]
        with self.assertRaisesRegex(RuntimeError,"LIFECYCLE_PHASES"):
            assurance.validate_plan(p)

    def test_missing_g24_at_intake_denied(self):
        p=deepcopy(PLAN)
        del p["workstreams"][0]["phases"]["INTAKE"]["G24"]
        with self.assertRaisesRegex(RuntimeError,"PHASE_ASSURANCE"):
            assurance.validate_plan(p)

    def test_missing_g23_mid_development_denied(self):
        p=deepcopy(PLAN)
        del p["workstreams"][1]["phases"]["DEVELOPMENT"]["G23"]
        with self.assertRaisesRegex(RuntimeError,"PHASE_ASSURANCE"):
            assurance.validate_plan(p)

    def test_g23_g24_cannot_swap_roles_or_self_sign(self):
        for role in ("G23","G24"):
            p=deepcopy(PLAN)
            p["workstreams"][2]["phases"]["INTEGRATION"][role]["decision_authority"]="BUILDER"
            with self.assertRaisesRegex(RuntimeError,"CANNOT_BE_SUBSTITUTED"):
                assurance.validate_plan(p)

    def test_all_four_workstreams_required(self):
        p=deepcopy(PLAN)
        p["workstreams"].pop()
        with self.assertRaisesRegex(RuntimeError,"WORKSTREAM_MISSING"):
            assurance.validate_plan(p)

    def test_risk_and_acceptance_mandatory_from_intake(self):
        for field,value in (("risks",[]),("acceptance",""),("dependencies",[])):
            p=deepcopy(PLAN)
            p["workstreams"][0][field]=value
            with self.assertRaises(RuntimeError):
                assurance.validate_plan(p)

    def test_incomplete_phase_rollbacks_denied(self):
        p=deepcopy(PLAN)
        p["workstreams"][3]["phases"]["POSTBOOT"]["rollback_condition"]=""
        with self.assertRaisesRegex(RuntimeError,"PHASE_CONTROL"):
            assurance.validate_plan(p)

    def test_stale_or_foreign_commit_evidence_denied(self):
        with self.assertRaisesRegex(RuntimeError,"CROSS_COMMIT"):
            assurance.evaluate(PLAN,SHA,[ref(commit="a"*40)])

    def test_evidence_id_replay_denied(self):
        r=ref()
        with self.assertRaisesRegex(RuntimeError,"CROSS_COMMIT"):
            assurance.evaluate(PLAN,SHA,[r,r])

    def test_evidence_reference_remains_untrusted_without_independent_signature(self):
        rows=[ref("G23_ONE"),ref("G24_ONE",role="G24")]
        report=assurance.evaluate(PLAN,SHA,rows)
        self.assertEqual(report["gate_slots_without_evidence_ref"],38)
        self.assertFalse(report["actual_signer_custody_attested"])
        self.assertFalse(report["certified"])
        self.assertEqual(report["life_cycle"][0]["workstreams"][0]["g23"]["evidence_refs"],
                         ["G23_ONE"])

    def test_cannot_submit_pass_or_certification_as_raw_evidence(self):
        row=ref()
        row["status"]="PASS"
        with self.assertRaisesRegex(RuntimeError,"CROSS_COMMIT"):
            assurance.evaluate(PLAN,SHA,[row])

    def test_plan_cannot_claim_inherited_certification(self):
        p=deepcopy(PLAN)
        p["activation_contract"]["historic_certification_is_not_current_authorization"]=False
        with self.assertRaisesRegex(RuntimeError,"ACTIVATION_CONTRACT"):
            assurance.validate_plan(p)

    def test_second_order_is_not_optional(self):
        p=deepcopy(PLAN)
        p["activation_contract"]["second_order"]=["G23_2"]
        with self.assertRaisesRegex(RuntimeError,"ACTIVATION_CONTRACT"):
            assurance.validate_plan(p)

    def test_cli_writes_exact_uncertified_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"receipt.json"
            rc=assurance.main(["--commit",SHA,"--out",str(out)])
            self.assertEqual(rc,0)
            receipt=json.loads(out.read_text())
            self.assertEqual(receipt["gate_slots"],40)
            self.assertFalse(receipt["certified"])
            self.assertEqual(assurance.main(["--commit",SHA,"--out",str(out)]),3)


if __name__=="__main__":
    unittest.main()
