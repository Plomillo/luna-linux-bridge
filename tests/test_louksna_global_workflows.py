from __future__ import annotations

import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
G23_PATH = ROOT / ".github/workflows/louksna-global-g23-independent-validation.yml"
G24_PATH = ROOT / ".github/workflows/louksna-global-g24-terminal-certification.yml"


def load_workflow(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)
    if not isinstance(parsed, dict):
        raise AssertionError(f"WORKFLOW_NOT_MAPPING:{path}")
    return parsed, raw


class LouksnaGlobalWorkflowDesignTests(unittest.TestCase):
    def test_g23_is_separate_trusted_and_candidate_code_is_data_only(self):
        workflow, raw = load_workflow(G23_PATH)
        self.assertEqual(workflow["name"], "Louksna global G23 independent validation")
        jobs = workflow.get("jobs", {})
        self.assertEqual(set(jobs), {"independent-validation"})
        job = jobs["independent-validation"]
        self.assertEqual(job["permissions"]["contents"], "read")
        self.assertEqual(job["permissions"]["id-token"], "write")
        self.assertEqual(job["permissions"]["attestations"], "write")
        steps = job["steps"]
        self.assertEqual(sum("actions/checkout@" in step.get("uses", "") for step in steps), 2)
        self.assertTrue(all(step.get("with", {}).get("persist-credentials") is False
                            for step in steps if "actions/checkout@" in step.get("uses", "")))
        self.assertIn("python3 -I trust-root/scripts/louksna_global_gate_ledger.py", raw)
        self.assertIn("actions/attest@", raw)
        self.assertIn("gh attestation verify", raw)
        self.assertIn("github.ref == 'refs/heads/main'", raw)
        self.assertNotIn("pull_request_target:", raw)

    def test_g24_rechecks_g23_on_a_distinct_runner_and_never_activates(self):
        workflow, raw = load_workflow(G24_PATH)
        self.assertEqual(workflow["name"], "Louksna global G24 terminal certification")
        jobs = workflow.get("jobs", {})
        self.assertEqual(set(jobs), {"terminal-decision"})
        job = jobs["terminal-decision"]
        self.assertEqual(job["permissions"]["contents"], "read")
        self.assertEqual(job["permissions"]["id-token"], "write")
        self.assertEqual(job["permissions"]["attestations"], "write")
        steps = job["steps"]
        self.assertTrue(any("actions/download-artifact@" in step.get("uses", "") for step in steps))
        self.assertIn("gh attestation verify", raw)
        self.assertIn("trust-root/scripts/louksna_global_gate_ledger.py", raw)
        self.assertIn("trust-root/scripts/louksna_g24_terminal_certifier.py", raw)
        self.assertIn("activation_authorized", (ROOT / "scripts/louksna_g24_terminal_certifier.py").read_text(encoding="utf-8"))
        self.assertIn("CERTIFIED_FOR_GLOBAL_CANONICAL_G01_G24", (ROOT / "scripts/louksna_g24_terminal_certifier.py").read_text(encoding="utf-8"))
        self.assertNotIn("pull_request_target:", raw)
        self.assertNotIn("activate_runtime", raw.lower())

    def test_policy_stays_fail_closed_until_exact_baseline_and_all_gate_evidence_exist(self):
        policy = yaml.safe_load((ROOT / "scripts/louksna_global_scope_policy.json").read_text(encoding="utf-8"))
        matrix = yaml.safe_load((ROOT / "scripts/louksna_global_gate_matrix.json").read_text(encoding="utf-8"))
        self.assertIsNone(policy["protected_baseline_sha256"])
        self.assertEqual(policy["status"], "HOLD_BASELINE_AND_CANONICAL_MATRIX_EVIDENCE_REQUIRED")
        self.assertEqual(len(matrix["gates"]), 24)
        self.assertTrue(all(row["status"] == "HOLD" for row in matrix["gates"]))
        self.assertTrue(all(row["acceptance_predicate"] is None and row["evidence"] == [] for row in matrix["gates"]))


if __name__ == "__main__":
    unittest.main()
