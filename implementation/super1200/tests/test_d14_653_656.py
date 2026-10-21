#!/usr/bin/env python3
"""Negative tests for D14 653-656. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d14_653_656 as tranche


class D14Tranche653656Tests(unittest.TestCase):
    def test_cap_0653(self):
        r = tranche.run(653, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HYPOTHESIS_COMPETITION_ENGINE')
        self.assertEqual(r["kind"], 'EPISTEMIC_ENGINE')
        self.assertEqual(r["binding"], 'hypothesis_competition_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(653, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(653, {"canonical_name": "OTHER"})
    def test_cap_0654(self):
        r = tranche.run(654, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BAYESIAN_BELIEF_UPDATE_ADAPTER')
        self.assertEqual(r["kind"], 'ANALYTICS_ADAPTER')
        self.assertEqual(r["binding"], 'bayesian_belief_update_adapter')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(654, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(654, {"canonical_name": "OTHER"})
    def test_cap_0655(self):
        r = tranche.run(655, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONFIDENCE_CALIBRATION_ENGINE')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'confidence_calibration_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(655, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(655, {"canonical_name": "OTHER"})
    def test_cap_0656(self):
        r = tranche.run(656, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RESIDUAL_UNCERTAINTY_REPORT')
        self.assertEqual(r["kind"], 'REPORT_ARTIFACT')
        self.assertEqual(r["binding"], 'residual_uncertainty_report')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(656, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(656, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
