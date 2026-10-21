#!/usr/bin/env python3
"""Negative tests for D12 583-585. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_583_585 as tranche


class D12Tranche583585Tests(unittest.TestCase):
    def test_cap_0583(self):
        r = tranche.run(583, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARCHITECTURAL_COST_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'architectural_cost_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(583, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(583, {"canonical_name": "OTHER"})
    def test_cap_0584(self):
        r = tranche.run(584, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AUTONOMY_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'autonomy_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(584, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(584, {"canonical_name": "OTHER"})
    def test_cap_0585(self):
        r = tranche.run(585, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MODEL_DEPENDENCE_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'model_dependence_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(585, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(585, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
