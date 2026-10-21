#!/usr/bin/env python3
"""Negative tests for D18 773-776. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_773_776 as tranche


class D18Tranche773776Tests(unittest.TestCase):
    def test_cap_0773(self):
        r = tranche.run(773, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_DEBT_LEDGER')
        self.assertEqual(r["kind"], 'LEDGER')
        self.assertEqual(r["binding"], 'maintenance_debt_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(773, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(773, {"canonical_name": "OTHER"})
    def test_cap_0774(self):
        r = tranche.run(774, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_DEBT_INTEREST')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'maintenance_debt_interest')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(774, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(774, {"canonical_name": "OTHER"})
    def test_cap_0775(self):
        r = tranche.run(775, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_BUDGET_ENGINE')
        self.assertEqual(r["kind"], 'RESOURCE_PLANNER')
        self.assertEqual(r["binding"], 'maintenance_budget_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(775, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(775, {"canonical_name": "OTHER"})
    def test_cap_0776(self):
        r = tranche.run(776, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_WINDOW_ENGINE')
        self.assertEqual(r["kind"], 'SCHEDULER')
        self.assertEqual(r["binding"], 'maintenance_window_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(776, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(776, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
