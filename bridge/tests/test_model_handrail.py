"""Negative proofs for LLM handrail: no invented G23/G24, no ignored GitHub runner."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import model_handrail as handrail

EVIDENCE = {"observations": {"run": {"sha256": "a"*64}}}


def valid():
    return {"schema": handrail.SCHEMA,
            "user_objective": "Inspect host exactly as authorized",
            "model_expectation": "Use already available read-only runner",
            "model": {"name": "SELF_DECLARED_TEST", "version": "TEST", "provider_verified": False},
            "tool_inventory": [{"name": "GITHUB_RUNNER_READONLY", "state": "AVAILABLE"}],
            "github_runner_considered": True,
            "claims": [{"statement": "A host read-only run has an available receipt",
                        "state": "OBSERVED", "evidence_refs": ["run"]}],
            "next_action": {"action": "OBSERVE_LOCAL", "kind": "READONLY_REGISTERED"},
            "pro_operational_review": {"rounds_completed": 3,
                                      "negative_tests_checked": 12,
                                      "claim_of_chatgpt_pro_control": False},
            "claimed_certified": False}


class HandrailTests(unittest.TestCase):
    def codes(self, result):
        return {row["code"] for row in result["corrections"]}

    def test_fully_structural_but_still_uncertified(self):
        report = handrail.review(valid(), EVIDENCE)
        self.assertEqual(report["status"], "STRUCTURAL_REVIEW_PASS_UNCERTIFIED")
        self.assertFalse(report["certified"])
        self.assertFalse(report["independent_evidence_verified"])

    def test_missing_version_must_be_fixed(self):
        x = valid()
        x["model"]["version"] = ""
        self.assertIn("MODEL_VERSION_MISSING", self.codes(handrail.review(x, EVIDENCE)))

    def test_user_requirements_cannot_be_dropped(self):
        x = valid()
        x["user_objective"] = ""
        self.assertIn("OWNER_GOAL_MISSING", self.codes(handrail.review(x, EVIDENCE)))

    def test_runner_must_not_be_ignored(self):
        x = valid()
        x["github_runner_considered"] = False
        self.assertIn("AVAILABLE_CHANNEL_IGNORED", self.codes(handrail.review(x, EVIDENCE)))

    def test_pro_mode_must_not_be_faked(self):
        x = valid()
        x["pro_operational_review"]["claim_of_chatgpt_pro_control"] = True
        self.assertIn("PRO_PRODUCT_MODE_OVERCLAIM", self.codes(handrail.review(x, EVIDENCE)))

    def test_verified_or_certified_self_claim_forbidden(self):
        for state in ("VERIFIED", "VALIDATED", "CERTIFIED"):
            x = valid()
            x["claims"][0]["state"] = state
            codes = self.codes(handrail.review(x, EVIDENCE))
            self.assertTrue(any("INDEPENDENT_VERIFICATION_NOT_PERFORMED" in c for c in codes))

    def test_forged_execution_without_receipt_denied(self):
        x = valid()
        x["claims"][0]["state"] = "EXECUTED"
        self.assertIn("MISSING_EXECUTION_RECEIPT_0", self.codes(handrail.review(x, EVIDENCE)))

    def test_unbound_evidence_denied(self):
        x = valid()
        x["claims"][0]["evidence_refs"] = ["fake-run"]
        self.assertIn("UNBOUND_EVIDENCE_0", self.codes(handrail.review(x, EVIDENCE)))

    def test_privileged_plan_cannot_self_authorize(self):
        x = valid()
        x["next_action"] = {"kind": "PROPOSE_GATED",
                            "action": "CAP_SUDO_BASH", "execution_authorized": True,
                            "fresh_g23": True, "fresh_g24": True}
        self.assertIn("GATED_AUTHORITY_OVERCLAIM", self.codes(handrail.review(x, EVIDENCE)))

    def test_unregistered_readonly_action_denied(self):
        x = valid()
        x["next_action"]["action"] = "SUDO_BASH"
        self.assertIn("READONLY_CAPABILITY_UNKNOWN", self.codes(handrail.review(x, EVIDENCE)))

    def test_evidence_hash_shape_required(self):
        bad = {"observations": {"run": {"sha256": "nonsense"}}}
        self.assertIn("UNBOUND_EVIDENCE_0", self.codes(handrail.review(valid(), bad)))

    def test_self_claimed_certified_does_not_pass(self):
        x = valid()
        x["claimed_certified"] = True
        self.assertIn("CERTIFICATION_SELF_ASSERTION", self.codes(handrail.review(x, EVIDENCE)))


if __name__ == "__main__":
    unittest.main()
