#!/usr/bin/env python3
"""Negative tests for D13 622-625. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_622_625 as tranche


class D13Tranche622625Tests(unittest.TestCase):
    def test_cap_0622(self):
        r = tranche.run(622, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPLANATION_REGRESSION_TEST')
        self.assertEqual(r["kind"], 'TEST_ENGINE')
        self.assertEqual(r["binding"], 'explanation_regression_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(622, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(622, {"canonical_name": "OTHER"})
    def test_cap_0623(self):
        r = tranche.run(623, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PEDAGOGICAL_VERSIONING')
        self.assertEqual(r["kind"], 'VERSIONING_POLICY')
        self.assertEqual(r["binding"], 'pedagogical_versioning')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(623, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(623, {"canonical_name": "OTHER"})
    def test_cap_0624(self):
        r = tranche.run(624, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CURRICULUM_GRAPH')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'curriculum_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(624, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(624, {"canonical_name": "OTHER"})
    def test_cap_0625(self):
        r = tranche.run(625, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CURRICULUM_COMPILER')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'curriculum_compiler')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(625, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(625, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
