#!/usr/bin/env python3
"""Negative tests for D13 634-637. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_634_637 as tranche


class D13Tranche634637Tests(unittest.TestCase):
    def test_cap_0634(self):
        r = tranche.run(634, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PEDAGOGICAL_EVIDENCE_LEDGER')
        self.assertEqual(r["kind"], 'LEDGER')
        self.assertEqual(r["binding"], 'pedagogical_evidence_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(634, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(634, {"canonical_name": "OTHER"})
    def test_cap_0635(self):
        r = tranche.run(635, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LEARNING_ANALYTICS_ENGINE')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'learning_analytics_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(635, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(635, {"canonical_name": "OTHER"})
    def test_cap_0636(self):
        r = tranche.run(636, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PEDAGOGICAL_COST_LEDGER')
        self.assertEqual(r["kind"], 'METRIC_LEDGER')
        self.assertEqual(r["binding"], 'pedagogical_cost_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(636, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(636, {"canonical_name": "OTHER"})
    def test_cap_0637(self):
        r = tranche.run(637, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPLANATION_QUALITY_GATE')
        self.assertEqual(r["kind"], 'QUALITY_GATE')
        self.assertEqual(r["binding"], 'explanation_quality_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(637, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(637, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
