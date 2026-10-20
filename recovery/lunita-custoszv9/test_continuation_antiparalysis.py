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

    def test_completion_gate_is_fail_closed_for_missing_or_unknown_results(self):
        self.assertIn("def completion_admitted(step_id, result):", self.patch)
        self.assertIn("if not completion_admitted(step_id, result):", self.patch)
        self.assertNotIn('if result.get("step_completion") is False:', self.patch)
        self.assertIn("STEP_SUCCESS_STATUS_ALLOWLIST", self.patch)
        self.assertIn("BLOCKED_STATUS_MARKERS", self.patch)

    def test_strict_beta_gates_require_explicit_true(self):
        self.assertIn("STRICT_STEP_COMPLETION_IDS", self.patch)
        self.assertIn('result.get("step_completion") is True', self.patch)
        self.assertIn('"S31_VERSIONED_BETA_RUNTIME_FUNCTIONAL_GATE"', self.patch)
        self.assertIn('"S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT"', self.patch)

    def test_blocked_attempt_returns_before_completion_append(self):
        blocked = self.patch.index("if not completion_admitted(step_id, result):")
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

    def test_independent_validation_is_not_inferred_from_nonfailure_status(self):
        self.assertIn("def independent_validation_state(result):", self.patch)
        self.assertIn('"independent_validation": independent_validation_state(result)', self.patch)
        self.assertIn("independent_report_sha256", self.patch)
        self.assertIn('"PENDING"', self.patch)

    def test_old_completion_claims_are_reconciled_without_deleting_history(self):
        self.assertIn("def reconcile_historical_completions(state):", self.patch)
        self.assertIn("historical_completion_adjudications", self.patch)
        self.assertIn("reconcile_historical_completions(state)", self.patch)

    def test_blocker_records_do_not_advance_the_progress_cursor(self):
        self.assertIn("step_index_preserved", self.patch)
        self.assertIn("state[\"step_index\"] = idx + 1", self.patch)
        self.assertIn("if not completion_admitted(step_id, result):", self.patch)

    def test_bounded_backoff_remains_present(self):
        self.assertIn("dt.timedelta(seconds=REFRESH_SECONDS)", self.patch)
        self.assertIn('"retry_after_seconds": REFRESH_SECONDS', self.patch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
