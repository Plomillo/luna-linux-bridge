#!/usr/bin/env python3
"""Negative tests for D17 729-732. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d17_729_732 as tranche


class D17Tranche729732Tests(unittest.TestCase):
    def test_cap_0729(self):
        r = tranche.run(729, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REASONING_STRATEGY_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'reasoning_strategy_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(729, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(729, {"canonical_name": "OTHER"})
    def test_cap_0730(self):
        r = tranche.run(730, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STRATEGY_SELECTION_ENGINE')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'strategy_selection_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(730, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(730, {"canonical_name": "OTHER"})
    def test_cap_0731(self):
        r = tranche.run(731, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STRATEGY_PERFORMANCE_HISTORY')
        self.assertEqual(r["kind"], 'LEDGER')
        self.assertEqual(r["binding"], 'strategy_performance_history')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(731, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(731, {"canonical_name": "OTHER"})
    def test_cap_0732(self):
        r = tranche.run(732, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPERT_HEURISTIC_REGISTRY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REGISTRY')
        self.assertEqual(r["binding"], 'expert_heuristic_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(732, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(732, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
