#!/usr/bin/env python3
"""Negative tests for D12 543-546. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_543_546 as tranche


class D12Tranche543546Tests(unittest.TestCase):
    def test_cap_0543(self):
        r = tranche.run(543, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PARTIAL_WRITE_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'partial_write_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(543, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(543, {"canonical_name": "OTHER"})
    def test_cap_0544(self):
        r = tranche.run(544, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RECOVERY_TIME_OBJECTIVE')
        self.assertEqual(r["kind"], 'METRIC/POLICY')
        self.assertEqual(r["binding"], 'recovery_time_objective')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(544, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(544, {"canonical_name": "OTHER"})
    def test_cap_0545(self):
        r = tranche.run(545, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RECOVERY_POINT_OBJECTIVE')
        self.assertEqual(r["kind"], 'METRIC/POLICY')
        self.assertEqual(r["binding"], 'recovery_point_objective')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(545, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(545, {"canonical_name": "OTHER"})
    def test_cap_0546(self):
        r = tranche.run(546, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RESILIENCE_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'resilience_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(546, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(546, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
