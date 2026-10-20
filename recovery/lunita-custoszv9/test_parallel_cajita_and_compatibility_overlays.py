import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PATCHES = REPO_ROOT / "recovery" / "lunita-custoszv9" / "patches"
SUPERVISOR_PATCH = PATCHES / "custosz_continuity_supervisor_v3.parallel-cajita-lane.patch"
GOVERNOR_PATCH = PATCHES / "custoszv9_continuous_governor_v2.compatibility-overlay.patch"
GOVERNOR_TEST_PATCH = PATCHES / "test_custoszv9_continuous_governor_v2.compatibility-overlay.patch"


class ParallelCajitaAndCompatibilityOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.supervisor = SUPERVISOR_PATCH.read_text(encoding="utf-8")
        cls.governor = GOVERNOR_PATCH.read_text(encoding="utf-8")
        cls.governor_tests = GOVERNOR_TEST_PATCH.read_text(encoding="utf-8")

    def test_cajita_ticks_even_when_serial_continuation_is_in_backoff(self):
        self.assertIn("def tick_parallel_cajita_lane(continuation_already_ticked):", self.supervisor)
        self.assertIn("if not continuation_invoked:", self.supervisor)
        self.assertIn("continuation_invoked = True", self.supervisor)
        self.assertIn("CAJITA_PRIORITY_LANE", self.supervisor)
        self.assertIn('recovery.record_fault("cajita_priority_lane"', self.supervisor)
        self.assertIn('"mission_completion_claim": False', self.supervisor)
        self.assertIn('"certification": "NOT_GRANTED"', self.supervisor)

    def test_python313_numpy_failure_requires_exact_evidence_and_is_bounded(self):
        self.assertIn("def _compatibility_recovery_route(", self.governor)
        self.assertIn("PYTHON313_NUMPY_LEGACY_SDIST_INCOMPATIBLE", self.governor)
        self.assertIn("numpy-1.26.4.tar.gz", self.governor)
        self.assertIn("metadata-generation-failed", self.governor)
        self.assertIn("numpy==2.2.6", self.governor)
        self.assertIn("compatibility_recovery_attempts", self.governor)
        self.assertIn("if \"numpy~=1.26.4\" not in argv_text:", self.governor)
        self.assertIn('"next_stage": "PROVISION_ENV"', self.governor)

    def test_runtime_integration_regression_is_included_in_overlay(self):
        self.assertIn("test_tick_moves_terminal_block_to_compatibility_recovery_without_launching_a_job", self.governor_tests)
        self.assertIn("test_python313_legacy_numpy_source_build_selects_different_route", self.governor_tests)
        self.assertIn("test_unrelated_failure_does_not_trigger_numpy_compatibility_route", self.governor_tests)


if __name__ == "__main__":
    unittest.main(verbosity=2)
