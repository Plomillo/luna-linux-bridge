#!/usr/bin/env python3
"""Negative tests for D17 725-728. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d17_725_728 as tranche


class D17Tranche725728Tests(unittest.TestCase):
    def test_cap_0725(self):
        r = tranche.run(725, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FOURTH_ORDER_ARCHITECTURE')
        self.assertEqual(r["kind"], 'ARCHITECTURE_LAYER')
        self.assertEqual(r["binding"], 'fourth_order_architecture')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(725, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(725, {"canonical_name": "OTHER"})
    def test_cap_0726(self):
        r = tranche.run(726, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FIFTH_ORDER_EVOLUTION')
        self.assertEqual(r["kind"], 'EVOLUTION_LAYER')
        self.assertEqual(r["binding"], 'fifth_order_evolution')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(726, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(726, {"canonical_name": "OTHER"})
    def test_cap_0727(self):
        r = tranche.run(727, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NTH_ORDER_EXTENSION_INTERFACE')
        self.assertEqual(r["kind"], 'EXTENSION_INTERFACE')
        self.assertEqual(r["binding"], 'nth_order_extension_interface')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(727, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(727, {"canonical_name": "OTHER"})
    def test_cap_0728(self):
        r = tranche.run(728, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'META_ASSUMPTION_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'meta_assumption_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(728, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(728, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
