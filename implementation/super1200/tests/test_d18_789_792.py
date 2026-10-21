#!/usr/bin/env python3
"""Negative tests for D18 789-792. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_789_792 as tranche


class D18Tranche789792Tests(unittest.TestCase):
    def test_cap_0789(self):
        r = tranche.run(789, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REGRESSION_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'regression_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(789, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(789, {"canonical_name": "OTHER"})
    def test_cap_0790(self):
        r = tranche.run(790, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REGRESSION_BISECTION_ENGINE')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'regression_bisection_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(790, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(790, {"canonical_name": "OTHER"})
    def test_cap_0791(self):
        r = tranche.run(791, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SEMANTIC_DIFF_ENGINE')
        self.assertEqual(r["kind"], 'DIFF_ENGINE')
        self.assertEqual(r["binding"], 'semantic_diff_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(791, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(791, {"canonical_name": "OTHER"})
    def test_cap_0792(self):
        r = tranche.run(792, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BEHAVIORAL_DIFF_ENGINE')
        self.assertEqual(r["kind"], 'DIFF_ENGINE')
        self.assertEqual(r["binding"], 'behavioral_diff_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(792, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(792, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
