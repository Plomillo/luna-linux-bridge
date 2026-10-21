#!/usr/bin/env python3
"""Negative tests for D11 489-492. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_489_492 as tranche


class D11Tranche489492Tests(unittest.TestCase):
    def test_cap_0489(self):
        r = tranche.run(489, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARCHITECTURAL_COST_BASELINE')
        self.assertEqual(r["kind"], 'BASELINE')
        self.assertEqual(r["binding"], 'architectural_cost_baseline')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(489, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(489, {"canonical_name": "OTHER"})
    def test_cap_0490(self):
        r = tranche.run(490, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COST_REGRESSION_DETECTOR')
        self.assertEqual(r["kind"], 'REGRESSION_ENGINE')
        self.assertEqual(r["binding"], 'cost_regression_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(490, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(490, {"canonical_name": "OTHER"})
    def test_cap_0491(self):
        r = tranche.run(491, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COST_IMPROVEMENT_DETECTOR')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'cost_improvement_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(491, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(491, {"canonical_name": "OTHER"})
    def test_cap_0492(self):
        r = tranche.run(492, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROCEDURE_SYNTHESIS')
        self.assertEqual(r["kind"], 'KNOWLEDGE_ENGINE')
        self.assertEqual(r["binding"], 'procedure_synthesis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(492, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(492, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
