#!/usr/bin/env python3
"""Negative tests for D18 821-824. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_821_824 as tranche


class D18Tranche821824Tests(unittest.TestCase):
    def test_cap_0821(self):
        r = tranche.run(821, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_FABRIC')
        self.assertEqual(r["kind"], 'UPDATE_FABRIC')
        self.assertEqual(r["binding"], 'update_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(821, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(821, {"canonical_name": "OTHER"})
    def test_cap_0822(self):
        r = tranche.run(822, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_CLASSIFIER')
        self.assertEqual(r["kind"], 'CLASSIFIER')
        self.assertEqual(r["binding"], 'update_classifier')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(822, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(822, {"canonical_name": "OTHER"})
    def test_cap_0823(self):
        r = tranche.run(823, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_RISK_SCORER')
        self.assertEqual(r["kind"], 'RISK_ENGINE')
        self.assertEqual(r["binding"], 'update_risk_scorer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(823, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(823, {"canonical_name": "OTHER"})
    def test_cap_0824(self):
        r = tranche.run(824, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PATCH_ELIGIBILITY_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'patch_eligibility_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(824, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(824, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
