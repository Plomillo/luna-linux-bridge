#!/usr/bin/env python3
"""Negative tests for D17 721-724. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d17_721_724 as tranche


class D17Tranche721724Tests(unittest.TestCase):
    def test_cap_0721(self):
        r = tranche.run(721, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'METACOGNITIVE_ORDER_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'metacognitive_order_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(721, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(721, {"canonical_name": "OTHER"})
    def test_cap_0722(self):
        r = tranche.run(722, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FIRST_ORDER_OBJECT_REASONING')
        self.assertEqual(r["kind"], 'REASONING_LAYER')
        self.assertEqual(r["binding"], 'first_order_object_reasoning')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(722, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(722, {"canonical_name": "OTHER"})
    def test_cap_0723(self):
        r = tranche.run(723, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECOND_ORDER_REASONING')
        self.assertEqual(r["kind"], 'METACOGNITIVE_LAYER')
        self.assertEqual(r["binding"], 'second_order_reasoning')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(723, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(723, {"canonical_name": "OTHER"})
    def test_cap_0724(self):
        r = tranche.run(724, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THIRD_ORDER_GOVERNANCE')
        self.assertEqual(r["kind"], 'GOVERNANCE_LAYER')
        self.assertEqual(r["binding"], 'third_order_governance')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(724, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(724, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
