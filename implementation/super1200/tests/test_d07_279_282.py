#!/usr/bin/env python3
"""Negative tests for D07 279-282. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_279_282 as tranche


class D07Tranche279282Tests(unittest.TestCase):
    def test_cap_0279(self):
        r = tranche.run(279, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TIME_SERIES_ENGINE')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'time_series_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(279, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(279, {"canonical_name": "OTHER"})
    def test_cap_0280(self):
        r = tranche.run(280, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SURVIVAL_ANALYSIS')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'survival_analysis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(280, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(280, {"canonical_name": "OTHER"})
    def test_cap_0281(self):
        r = tranche.run(281, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MONTE_CARLO_ENGINE')
        self.assertEqual(r["kind"], 'SIMULATION_ENGINE')
        self.assertEqual(r["binding"], 'monte_carlo_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(281, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(281, {"canonical_name": "OTHER"})
    def test_cap_0282(self):
        r = tranche.run(282, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OPTIMIZATION_ENGINE')
        self.assertEqual(r["kind"], 'MATHEMATICAL_ENGINE')
        self.assertEqual(r["binding"], 'optimization_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(282, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(282, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
