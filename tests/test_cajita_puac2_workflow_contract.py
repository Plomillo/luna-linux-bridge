import re
import unittest
from pathlib import Path

import yaml


WORKFLOW_PATH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "cajita-luna-puac2-g23-g24.yml"
SHA_PIN_RE = re.compile(r"^[0-9a-f]{40}$")


class CajitaTrustedWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.workflow = yaml.safe_load(cls.text)

    def test_github_expression_interpolation_is_not_backslash_escaped(self):
        token = chr(36) + "{{"
        self.assertNotIn("\\" + token, self.text)
        self.assertIn(token + " inputs.candidate_commit }}", self.text)
        self.assertIn(token + " inputs.expected_subject_sha256 }}", self.text)
        self.assertIn(token + " vars.CAJITA_LUNA_ROOT }}", self.text)
        self.assertIn("workflow_dispatch:", self.text)

    def test_workflow_has_separate_g23_g24_and_persist_jobs(self):
        jobs = self.workflow["jobs"]
        self.assertEqual(
            set(jobs),
            {"g23-independent-validation", "g24-independent-certification", "persist-and-final-readback"},
        )
        self.assertEqual(jobs["g23-independent-validation"]["runs-on"], ["self-hosted", "linux", "x64", "luna-aux"])
        self.assertEqual(jobs["g24-independent-certification"]["runs-on"], "ubuntu-latest")
        self.assertEqual(jobs["g24-independent-certification"]["needs"], "g23-independent-validation")
        self.assertEqual(
            set(jobs["persist-and-final-readback"]["needs"]),
            {"g23-independent-validation", "g24-independent-certification"},
        )
        for name in jobs:
            self.assertEqual(jobs[name]["if"], "github.ref == 'refs/heads/main'")

    def test_signing_secrets_are_scoped_to_their_own_jobs(self):
        jobs = self.workflow["jobs"]
        g23_text = str(jobs["g23-independent-validation"])
        g24_text = str(jobs["g24-independent-certification"])
        persist_text = str(jobs["persist-and-final-readback"])
        self.assertIn("CAJITA_G23_SIGNING_PRIVATE_KEY_PEM", g23_text)
        self.assertNotIn("CAJITA_G24_SIGNING_PRIVATE_KEY_PEM", g23_text)
        self.assertIn("CAJITA_G23_PUBLIC_KEY_PEM", g24_text)
        self.assertIn("CAJITA_G24_SIGNING_PRIVATE_KEY_PEM", g24_text)
        self.assertNotIn("CAJITA_G23_SIGNING_PRIVATE_KEY_PEM", g24_text)
        self.assertIn("CAJITA_G23_PUBLIC_KEY_PEM", persist_text)
        self.assertIn("CAJITA_G24_PUBLIC_KEY_PEM", persist_text)
        self.assertNotIn("CAJITA_G24_SIGNING_PRIVATE_KEY_PEM", persist_text)

    def test_action_references_are_pinned_and_checkout_credentials_are_not_persisted(self):
        for job in self.workflow["jobs"].values():
            for step in job.get("steps", []):
                uses = step.get("uses")
                if not uses:
                    continue
                action, at, version = uses.partition("@")
                self.assertTrue(at, f"Action ref missing: {uses}")
                if action.startswith("actions/"):
                    self.assertRegex(version, SHA_PIN_RE, f"Action must be pinned to a full SHA: {uses}")
                if action == "actions/checkout":
                    self.assertIs(step.get("with", {}).get("persist-credentials"), False)


    def test_g23_and_final_readback_fetch_pinned_helper_source_history(self):
        jobs = self.workflow["jobs"]
        for job_id in ("g23-independent-validation", "persist-and-final-readback"):
            checkouts = [
                step for step in jobs[job_id]["steps"]
                if step.get("uses", "").startswith("actions/checkout@")
                and step.get("with", {}).get("ref") == "main"
            ]
            self.assertTrue(checkouts, f"No trusted main checkout in {job_id}")
            self.assertIs(checkouts[0].get("with", {}).get("fetch-depth"), 0)


    def test_artifact_paths_only_upload_compact_gate_receipts(self):
        self.assertNotRegex(self.text, r"^\s*-\s+.*\.(?:7z|safetensors|gguf|apk)\s*$")
        self.assertIn("G23_SIGNED.json", self.text)
        self.assertIn("G24_SIGNED.json", self.text)
        self.assertIn("persist-bundle", self.text)
        self.assertIn("FINAL_VERIFICATION.json", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
