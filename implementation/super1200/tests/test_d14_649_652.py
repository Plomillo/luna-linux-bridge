#!/usr/bin/env python3
"""Negative tests for D14 649-652. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d14_649_652 as tranche


class D14Tranche649652Tests(unittest.TestCase):
    def test_cap_0649(self):
        r = tranche.run(649, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EVIDENCE_GAP_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'evidence_gap_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(649, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(649, {"canonical_name": "OTHER"})
    def test_cap_0650(self):
        r = tranche.run(650, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INFORMATION_ACQUISITION_PLANNER')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'information_acquisition_planner')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(650, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(650, {"canonical_name": "OTHER"})
    def test_cap_0651(self):
        r = tranche.run(651, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'VALUE_OF_INFORMATION_ENGINE')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'value_of_information_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(651, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(651, {"canonical_name": "OTHER"})
    def test_cap_0652(self):
        r = tranche.run(652, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CHEAPEST_DISCRIMINATING_TEST')
        self.assertEqual(r["kind"], 'TEST_PLANNER')
        self.assertEqual(r["binding"], 'cheapest_discriminating_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(652, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(652, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
