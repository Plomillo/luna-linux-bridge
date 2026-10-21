#!/usr/bin/env python3
"""Negative tests for D07 275-278. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_275_278 as tranche


class D07Tranche275278Tests(unittest.TestCase):
    def test_cap_0275(self):
        r = tranche.run(275, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STAN_PROVIDER')
        self.assertEqual(r["kind"], 'PROBABILISTIC_LANGUAGE_TOOLCHAIN')
        self.assertEqual(r["binding"], 'stan_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(275, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(275, {"canonical_name": "OTHER"})
    def test_cap_0276(self):
        r = tranche.run(276, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPERIMENT_DESIGN_ENGINE')
        self.assertEqual(r["kind"], 'RESEARCH_ENGINE')
        self.assertEqual(r["binding"], 'experiment_design_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(276, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(276, {"canonical_name": "OTHER"})
    def test_cap_0277(self):
        r = tranche.run(277, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'POWER_ANALYSIS')
        self.assertEqual(r["kind"], 'STATISTICAL_ENGINE')
        self.assertEqual(r["binding"], 'power_analysis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(277, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(277, {"canonical_name": "OTHER"})
    def test_cap_0278(self):
        r = tranche.run(278, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CAUSAL_INFERENCE_ENGINE')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'causal_inference_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(278, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(278, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
