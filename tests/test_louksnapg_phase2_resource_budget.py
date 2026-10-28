"""Hosted-runner resource policy tests; imports no model weights and performs no inference."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "cajita-luna-runtime"))

from tools.louksnapg_phase2_functional import (
    calculate_hosted_runner_rss_budget_bytes,
    parse_cgroup_memory_limit_bytes,
    parse_mem_total_bytes,
    require_hosted_runner,
)


class HostedRunnerResourceBudgetTests(unittest.TestCase):
    def test_local_execution_is_rejected_before_model_work(self):
        with self.assertRaisesRegex(RuntimeError, "HEAVY_MODEL_INFERENCE_REQUIRES_GITHUB_HOSTED_RUNNER"):
            require_hosted_runner({"GITHUB_ACTIONS": "false"})

    def test_github_hosted_runner_is_admitted(self):
        require_hosted_runner({"GITHUB_ACTIONS": "true"})

    def test_runner_budget_is_derived_from_effective_cloud_limit_not_local_one_gib(self):
        mem_total = 8 * 1024**3
        cgroup_limit = 6 * 1024**3
        decision = calculate_hosted_runner_rss_budget_bytes(mem_total, cgroup_limit)
        self.assertEqual(decision["effective_memory_limit_bytes"], cgroup_limit)
        self.assertEqual(decision["rss_budget_bytes"], int(cgroup_limit * 0.75))
        self.assertGreater(decision["rss_budget_bytes"], 1024**3)
        self.assertFalse(decision["local_inspection_budget_applied"])

    def test_explicit_hosted_runner_override_is_recorded_and_not_silently_capped(self):
        override = 2 * 1024**3
        decision = calculate_hosted_runner_rss_budget_bytes(8 * 1024**3, 6 * 1024**3, override_bytes=override)
        self.assertEqual(decision["rss_budget_bytes"], override)
        self.assertEqual(decision["budget_source"], "LOUKSNAPG_HOSTED_RUNNER_RSS_CAP_BYTES")
        self.assertFalse(decision["local_inspection_budget_applied"])

    def test_override_above_physical_budget_is_capped(self):
        decision = calculate_hosted_runner_rss_budget_bytes(
            8 * 1024**3, 6 * 1024**3, override_bytes=12 * 1024**3
        )
        self.assertEqual(decision["rss_budget_bytes"], int(6 * 1024**3 * 0.75))
        self.assertIn("CAPPED_TO_RUNNER_MEMORY", decision["budget_source"])

    def test_memory_metadata_parsing(self):
        self.assertEqual(parse_mem_total_bytes("MemTotal:       8388608 kB\nMemAvailable:   4000000 kB\n"), 8388608 * 1024)
        self.assertIsNone(parse_cgroup_memory_limit_bytes("max\n"))
        self.assertEqual(parse_cgroup_memory_limit_bytes(str(6 * 1024**3)), 6 * 1024**3)

    def test_invalid_override_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "HOSTED_RUNNER_RSS_OVERRIDE_INVALID"):
            calculate_hosted_runner_rss_budget_bytes(8 * 1024**3, override_bytes=-1)


if __name__ == "__main__":
    unittest.main()
