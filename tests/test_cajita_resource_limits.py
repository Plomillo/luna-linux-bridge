from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

RUNTIME = Path(__file__).resolve().parents[1] / "cajita-luna-runtime"
sys.path.insert(0, str(RUNTIME))

import cajita_resource_limits as limits


GIB = 1024**3


def write_cgroup(root: Path, memory: int, cpu: str = "100000 100000", swap: str = "0") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cgroup.controllers").write_text("cpu memory\n", encoding="ascii")
    (root / "memory.max").write_text(str(memory), encoding="ascii")
    (root / "cpu.max").write_text(cpu, encoding="ascii")
    (root / "memory.swap.max").write_text(swap, encoding="ascii")


class CajitaResourceLimitsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.previous_root = limits.CGROUP_ROOT
        limits.CGROUP_ROOT = self.root
        write_cgroup(self.root, GIB)

    def tearDown(self):
        limits.CGROUP_ROOT = self.previous_root
        self.temp.cleanup()

    def test_candidate_and_repair_contracts_are_distinct(self):
        candidate = limits.candidate_policy()
        repair = limits.repair_policy()
        self.assertEqual(candidate["memory_limit_bytes"], GIB)
        self.assertEqual(candidate["cpu_count"], 1)
        self.assertEqual(repair["memory_limit_bytes"], 3 * GIB)
        self.assertEqual(repair["cpu_count"], 1)
        self.assertNotEqual(candidate["memory_limit_bytes"], repair["memory_limit_bytes"])

    def test_exact_candidate_cgroup_is_verified_and_zero_swap_is_valid(self):
        observed = limits.verify_cgroup_budget(GIB, 1)
        self.assertEqual(observed["memory_limit_bytes"], GIB)
        self.assertEqual(observed["cpu_count"], 1)
        self.assertEqual(observed["cpu_limit_cores"], 1.0)
        self.assertEqual(observed["memory_swap_limit_bytes"], 0)
        self.assertEqual(observed["memory_swap_policy"], "SWAP_DISABLED")

    def test_repair_requires_exact_three_gib_cgroup(self):
        write_cgroup(self.root, 3 * GIB)
        result = limits.verify_cgroup_budget(3 * GIB, 1)
        self.assertEqual(result["memory_limit_bytes"], 3 * GIB)
        self.assertEqual(result["memory_limit_gib"], 3.0)

    def test_memory_mismatch_is_fail_closed(self):
        with self.assertRaisesRegex(limits.ResourcePolicyError, "CGROUP_MEMORY_BUDGET_MISMATCH"):
            limits.verify_cgroup_budget(3 * GIB, 1)

    def test_unbounded_memory_is_rejected(self):
        (self.root / "memory.max").write_text("max", encoding="ascii")
        with self.assertRaisesRegex(limits.ResourcePolicyError, "CGROUP_V2_LIMIT_UNBOUNDED"):
            limits.verify_cgroup_budget(GIB, 1)

    def test_more_than_one_cpu_is_rejected(self):
        with self.assertRaisesRegex(limits.ResourcePolicyError, "CPU_BUDGET_MUST_EQUAL_ONE"):
            limits.verify_cgroup_budget(GIB, 2)

    def test_cpu_quota_above_one_core_is_rejected(self):
        write_cgroup(self.root, GIB, cpu="200000 100000")
        with self.assertRaisesRegex(limits.ResourcePolicyError, "CGROUP_CPU_BUDGET_EXCEEDS_ONE_CORE"):
            limits.verify_cgroup_budget(GIB, 1)

    def test_apply_limits_verifies_cgroup_and_affinity(self):
        with patch.object(limits.os, "sched_getaffinity", side_effect=[{2, 3}, {2}]), \
             patch.object(limits.os, "sched_setaffinity") as set_affinity:
            result = limits.apply_process_limits(GIB, 1)
        self.assertEqual(result["status"], "PASS_CGROUP_AND_CPU_AFFINITY_VERIFIED")
        self.assertEqual(result["cpu_affinity"], [2])
        set_affinity.assert_called_once_with(0, {2})
        self.assertEqual(result["process_virtual_address_limit"], "NOT_USED")

    def test_child_preexec_uses_the_candidate_budget(self):
        hook = limits.child_preexec_fn()
        with patch.object(limits, "apply_process_limits") as apply:
            hook()
        apply.assert_called_once_with(GIB, 1)

    def test_child_preexec_rejects_wrong_cpu_budget(self):
        with self.assertRaisesRegex(limits.ResourcePolicyError, "CPU_BUDGET_MUST_EQUAL_ONE"):
            limits.child_preexec_fn(memory_bytes=GIB, cpu_count=2)

    def test_swap_max_unbounded_does_not_confuse_ram_limit(self):
        write_cgroup(self.root, GIB, swap="max")
        result = limits.verify_cgroup_budget(GIB, 1)
        self.assertIsNone(result["memory_swap_limit_bytes"])
        self.assertEqual(result["memory_limit_bytes"], GIB)


if __name__ == "__main__":
    unittest.main()
