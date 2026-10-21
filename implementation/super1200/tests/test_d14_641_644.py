#!/usr/bin/env python3
"""Negative tests for D14 641-644. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d14_641_644 as tranche


class D14Tranche641644Tests(unittest.TestCase):
    def test_cap_0641(self):
        r = tranche.run(641, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_REDUCTION_FABRIC')
        self.assertEqual(r["kind"], 'EPISTEMIC_FABRIC')
        self.assertEqual(r["binding"], 'uncertainty_reduction_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(641, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(641, {"canonical_name": "OTHER"})
    def test_cap_0642(self):
        r = tranche.run(642, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_ORIGIN_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'uncertainty_origin_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(642, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(642, {"canonical_name": "OTHER"})
    def test_cap_0643(self):
        r = tranche.run(643, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_TAXONOMY')
        self.assertEqual(r["kind"], 'ONTOLOGY')
        self.assertEqual(r["binding"], 'uncertainty_taxonomy')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(643, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(643, {"canonical_name": "OTHER"})
    def test_cap_0644(self):
        r = tranche.run(644, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_BUDGET')
        self.assertEqual(r["kind"], 'POLICY')
        self.assertEqual(r["binding"], 'uncertainty_budget')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(644, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(644, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
