#!/usr/bin/env python3
"""Negative tests for D18 769-772. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_769_772 as tranche


class D18Tranche769772Tests(unittest.TestCase):
    def test_cap_0769(self):
        r = tranche.run(769, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ADAPTIVE_MAINTENANCE_ENGINE')
        self.assertEqual(r["kind"], 'MAINTENANCE_ENGINE')
        self.assertEqual(r["binding"], 'adaptive_maintenance_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(769, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(769, {"canonical_name": "OTHER"})
    def test_cap_0770(self):
        r = tranche.run(770, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EVOLUTIONARY_MAINTENANCE_ENGINE')
        self.assertEqual(r["kind"], 'MAINTENANCE_ENGINE')
        self.assertEqual(r["binding"], 'evolutionary_maintenance_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(770, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(770, {"canonical_name": "OTHER"})
    def test_cap_0771(self):
        r = tranche.run(771, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_PRIORITY_ENGINE')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'maintenance_priority_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(771, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(771, {"canonical_name": "OTHER"})
    def test_cap_0772(self):
        r = tranche.run(772, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_COST_LEDGER')
        self.assertEqual(r["kind"], 'LEDGER')
        self.assertEqual(r["binding"], 'maintenance_cost_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(772, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(772, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
