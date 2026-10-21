#!/usr/bin/env python3
"""Negative tests for D11 497-500. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_497_500 as tranche


class D11Tranche497500Tests(unittest.TestCase):
    def test_cap_0497(self):
        r = tranche.run(497, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REPEATED_WORK_DETECTOR')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'repeated_work_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(497, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(497, {"canonical_name": "OTHER"})
    def test_cap_0498(self):
        r = tranche.run(498, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HUMAN_FRICTION_DETECTOR')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'human_friction_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(498, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(498, {"canonical_name": "OTHER"})
    def test_cap_0499(self):
        r = tranche.run(499, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MODEL_FRICTION_DETECTOR')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'model_friction_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(499, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(499, {"canonical_name": "OTHER"})
    def test_cap_0500(self):
        r = tranche.run(500, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INFRASTRUCTURE_GAP_INFERENCE')
        self.assertEqual(r["kind"], 'METACOGNITIVE_ANALYZER')
        self.assertEqual(r["binding"], 'infrastructure_gap_inference')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(500, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(500, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
