#!/usr/bin/env python3
"""Negative tests for D18 785-788. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_785_788 as tranche


class D18Tranche785788Tests(unittest.TestCase):
    def test_cap_0785(self):
        r = tranche.run(785, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REVERSE_DEPENDENCY_ANALYZER')
        self.assertEqual(r["kind"], 'GRAPH_ANALYZER')
        self.assertEqual(r["binding"], 'reverse_dependency_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(785, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(785, {"canonical_name": "OTHER"})
    def test_cap_0786(self):
        r = tranche.run(786, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AFFECTED_TEST_SELECTOR')
        self.assertEqual(r["kind"], 'TEST_PLANNER')
        self.assertEqual(r["binding"], 'affected_test_selector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(786, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(786, {"canonical_name": "OTHER"})
    def test_cap_0787(self):
        r = tranche.run(787, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FULL_REGRESSION_ESCALATOR')
        self.assertEqual(r["kind"], 'POLICY_ENGINE')
        self.assertEqual(r["binding"], 'full_regression_escalator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(787, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(787, {"canonical_name": "OTHER"})
    def test_cap_0788(self):
        r = tranche.run(788, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REGRESSION_FIRST_POLICY')
        self.assertEqual(r["kind"], 'POLICY')
        self.assertEqual(r["binding"], 'regression_first_policy')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(788, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(788, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
