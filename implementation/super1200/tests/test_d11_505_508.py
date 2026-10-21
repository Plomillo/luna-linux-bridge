#!/usr/bin/env python3
"""Negative tests for D11 505-508. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_505_508 as tranche


class D11Tranche505508Tests(unittest.TestCase):
    def test_cap_0505(self):
        r = tranche.run(505, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INFORMATION_GAIN_ESTIMATOR')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'information_gain_estimator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(505, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(505, {"canonical_name": "OTHER"})
    def test_cap_0506(self):
        r = tranche.run(506, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPERIMENT_VALUE_ESTIMATOR')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'experiment_value_estimator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(506, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(506, {"canonical_name": "OTHER"})
    def test_cap_0507(self):
        r = tranche.run(507, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STOP_RESEARCH_CRITERIA')
        self.assertEqual(r["kind"], 'POLICY')
        self.assertEqual(r["binding"], 'stop_research_criteria')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(507, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(507, {"canonical_name": "OTHER"})
    def test_cap_0508(self):
        r = tranche.run(508, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DIMINISHING_RETURNS_DETECTOR')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'diminishing_returns_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(508, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(508, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
