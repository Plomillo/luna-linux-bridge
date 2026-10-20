import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATCH = ROOT / "recovery/lunita-custoszv9/patches/custosz_mision1_continuation_v1.antiparalysis.patch"

class AntiParalysisPatchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text(encoding="utf-8")

    def test_runtime_and_independent_gates_are_appended(self):
        self.assertIn("S31_VERSIONED_BETA_RUNTIME_FUNCTIONAL_GATE", self.patch)
        self.assertIn("S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT", self.patch)

    def test_blocked_step_requires_explicit_false(self):
        self.assertIn('if result.get("step_completion") is False:', self.patch)

    def test_blocked_attempt_returns_before_completion_append(self):
        blocked = self.patch.index('if result.get("step_completion") is False:')
        clear_block = self.patch.index('state.pop("blocked_step", None)', blocked)
        append_completed = self.patch.index('state.setdefault("completed_steps", []).append({', clear_block)
        blocked_path = self.patch[blocked:clear_block]
        self.assertLess(blocked, clear_block)
        self.assertLess(clear_block, append_completed)
        self.assertIn('"step_index_preserved": idx', blocked_path)
        self.assertIn('"step_completion": False', blocked_path)
        self.assertIn("atomic(PROGRESS, state)", blocked_path)
        self.assertIn("return {", blocked_path)
        self.assertNotIn('state["step_index"] = idx + 1', blocked_path)

    def test_bounded_retry_and_progress_timestamp(self):
        self.assertIn("dt.timedelta(seconds=REFRESH_SECONDS)", self.patch)
        self.assertIn('"last_progress_utc": state.get("last_progress_utc")', self.patch)
        self.assertIn('"retry_after_seconds": REFRESH_SECONDS', self.patch)

    def test_independent_report_binds_exact_runtime_hash(self):
        self.assertIn('independent.get("runtime_report_sha256") != expected_runtime_sha', self.patch)
        self.assertIn('"canonical_g06_certification":"NOT_GRANTED"', self.patch)
        self.assertIn('"canonical_g08_bindings_mutated":False', self.patch)

if __name__ == "__main__":
    unittest.main(verbosity=2)
