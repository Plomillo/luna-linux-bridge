#!/usr/bin/env python3
"""Negative tests for D07 283-286. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_283_286 as tranche


class D07Tranche283286Tests(unittest.TestCase):
    def test_cap_0283(self):
        r = tranche.run(283, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OPERATIONS_RESEARCH_ENGINE')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'operations_research_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(283, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(283, {"canonical_name": "OTHER"})
    def test_cap_0284(self):
        r = tranche.run(284, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_QUANTIFICATION')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'uncertainty_quantification')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(284, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(284, {"canonical_name": "OTHER"})
    def test_cap_0285(self):
        r = tranche.run(285, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SENSITIVITY_ANALYSIS')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'sensitivity_analysis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(285, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(285, {"canonical_name": "OTHER"})
    def test_cap_0286(self):
        r = tranche.run(286, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUALITATIVE_RESEARCH_FABRIC')
        self.assertEqual(r["kind"], 'RESEARCH_FABRIC')
        self.assertEqual(r["binding"], 'qualitative_research_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(286, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(286, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
