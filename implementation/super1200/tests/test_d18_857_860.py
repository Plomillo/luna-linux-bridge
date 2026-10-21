#!/usr/bin/env python3
"""Negative tests for D18 857-860. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_857_860 as tranche


class D18Tranche857860Tests(unittest.TestCase):
    def test_cap_0857(self):
        r = tranche.run(857, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TOIL_ELIMINATION_ENGINE')
        self.assertEqual(r["kind"], 'AUTOMATION_FACTORY')
        self.assertEqual(r["binding"], 'toil_elimination_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(857, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(857, {"canonical_name": "OTHER"})
    def test_cap_0858(self):
        r = tranche.run(858, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_COST_REGRESSION_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'maintenance_cost_regression_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(858, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(858, {"canonical_name": "OTHER"})
    def test_cap_0859(self):
        r = tranche.run(859, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTAINABILITY_NON_REGRESSION_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'maintainability_non_regression_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(859, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(859, {"canonical_name": "OTHER"})
    def test_cap_0860(self):
        r = tranche.run(860, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_COMPRESSION_RATIO')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'maintenance_compression_ratio')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(860, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(860, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
