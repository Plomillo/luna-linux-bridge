from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

RUNTIME = Path(__file__).resolve().parents[1] / "cajita-luna-runtime"
sys.path.insert(0, str(RUNTIME))

import cajita_resource_limits as limits


class CandidateResourceLimitTests(unittest.TestCase):
    def test_candidate_budget_is_exactly_one_gib_and_one_core(self):
        policy = limits.candidate_policy()
        self.assertEqual(policy["memory_limit_bytes"], 1024**3)
        self.assertEqual(policy["memory_limit_gib"], 1)
        self.assertEqual(policy["cpu_count"], 1)
        self.assertEqual(policy["memory_limit_mechanism"], "RLIMIT_AS_SOFT_AND_HARD_PER_PROCESS")
        self.assertEqual(policy["cpu_limit_mechanism"], "SCHED_SETAFFINITY")
        self.assertEqual(policy["aggregate_cgroup_rss_limit"], "NOT_CLAIMED")

    def test_apply_limits_sets_hard_address_space_and_single_cpu_affinity(self):
        with (
            patch.object(limits.os, "sched_getaffinity", side_effect=[{2, 3}, {2}]),
            patch.object(limits.os, "sched_setaffinity") as set_affinity,
            patch.object(limits.resource, "getrlimit", return_value=(limits.resource.RLIM_INFINITY, limits.resource.RLIM_INFINITY)),
            patch.object(limits.resource, "setrlimit") as set_rlimit,
        ):
            result = limits.apply_process_limits(1024**3, 1)
        self.assertEqual(result["status"], "PASS_PROCESS_LIMITS_APPLIED")
        self.assertEqual(result["memory_limit_bytes"], 1024**3)
        self.assertEqual(result["cpu_affinity"], [2])
        set_affinity.assert_called_once_with(0, {2})
        set_rlimit.assert_called_once_with(limits.resource.RLIMIT_AS, (1024**3, 1024**3))

    def test_rejects_more_than_one_cpu(self):
        with self.assertRaisesRegex(limits.ResourcePolicyError, "CANDIDATE_CPU_BUDGET_MUST_EQUAL_ONE"):
            limits.apply_process_limits(1024**3, 2)

    def test_child_preexec_applies_limits_before_model_import(self):
        with patch.object(limits, "apply_process_limits", return_value={"status": "PASS"}) as apply:
            hook = limits.child_preexec_fn()
            hook()
        apply.assert_called_once_with(1024**3, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
