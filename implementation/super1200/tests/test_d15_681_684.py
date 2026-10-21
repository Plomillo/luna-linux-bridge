#!/usr/bin/env python3
"""Negative tests for D15 681-684. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d15_681_684 as tranche


class D15Tranche681684Tests(unittest.TestCase):
    def test_cap_0681(self):
        r = tranche.run(681, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REPAIRABILITY_CLASSIFIER')
        self.assertEqual(r["kind"], 'CLASSIFIER')
        self.assertEqual(r["binding"], 'repairability_classifier')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(681, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(681, {"canonical_name": "OTHER"})
    def test_cap_0682(self):
        r = tranche.run(682, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REPAIR_PLAN_ENGINE')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'repair_plan_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(682, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(682, {"canonical_name": "OTHER"})
    def test_cap_0683(self):
        r = tranche.run(683, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REPAIR_RISK_ANALYZER')
        self.assertEqual(r["kind"], 'RISK_ENGINE')
        self.assertEqual(r["binding"], 'repair_risk_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(683, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(683, {"canonical_name": "OTHER"})
    def test_cap_0684(self):
        r = tranche.run(684, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SAFE_REPAIR_SANDBOX')
        self.assertEqual(r["kind"], 'SANDBOX')
        self.assertEqual(r["binding"], 'safe_repair_sandbox')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(684, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(684, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
