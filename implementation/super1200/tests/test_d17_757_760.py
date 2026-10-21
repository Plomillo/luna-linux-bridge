#!/usr/bin/env python3
"""Negative tests for D17 757-760. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d17_757_760 as tranche


class D17Tranche757760Tests(unittest.TestCase):
    def test_cap_0757(self):
        r = tranche.run(757, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ECOSYSTEM_NON_DUPLICATION_GATE')
        self.assertEqual(r["kind"], 'G16_GATE')
        self.assertEqual(r["binding"], 'ecosystem_non_duplication_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(757, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(757, {"canonical_name": "OTHER"})
    def test_cap_0758(self):
        r = tranche.run(758, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AMBITION_EXPANSION_ENGINE')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'ambition_expansion_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(758, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(758, {"canonical_name": "OTHER"})
    def test_cap_0759(self):
        r = tranche.run(759, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AMBITION_CONTRACTION_ENGINE')
        self.assertEqual(r["kind"], 'DECOMMISSION_PLANNER')
        self.assertEqual(r["binding"], 'ambition_contraction_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(759, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(759, {"canonical_name": "OTHER"})
    def test_cap_0760(self):
        r = tranche.run(760, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANTI_HEADACHE_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'anti_headache_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(760, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(760, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
