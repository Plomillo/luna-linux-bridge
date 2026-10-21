#!/usr/bin/env python3
"""Negative tests for D21 1005-1008. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1005_1008 as tranche


class D21Tranche10051008Tests(unittest.TestCase):
    def test_cap_1005(self):
        r = tranche.run(1005, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONTENT_VALUE_CLASSIFIER')
        self.assertEqual(r["kind"], 'CLASSIFIER')
        self.assertEqual(r["binding"], 'content_value_classifier')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1005, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1005, {"canonical_name": "OTHER"})
    def test_cap_1006(self):
        r = tranche.run(1006, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SANITIZATION_FEASIBILITY_ENGINE')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'sanitization_feasibility_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1006, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1006, {"canonical_name": "OTHER"})
    def test_cap_1007(self):
        r = tranche.run(1007, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SURGICAL_REMOVAL_PLANNER')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'surgical_removal_planner')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1007, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1007, {"canonical_name": "OTHER"})
    def test_cap_1008(self):
        r = tranche.run(1008, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SAFE_RECONSTRUCTION_ENGINE')
        self.assertEqual(r["kind"], 'SANITIZATION_ENGINE')
        self.assertEqual(r["binding"], 'safe_reconstruction_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1008, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1008, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
