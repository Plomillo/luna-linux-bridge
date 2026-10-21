#!/usr/bin/env python3
"""Negative tests for D18 765-768. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_765_768 as tranche


class D18Tranche765768Tests(unittest.TestCase):
    def test_cap_0765(self):
        r = tranche.run(765, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_DAG')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'maintenance_dag')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(765, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(765, {"canonical_name": "OTHER"})
    def test_cap_0766(self):
        r = tranche.run(766, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_PLANNER')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'maintenance_planner')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(766, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(766, {"canonical_name": "OTHER"})
    def test_cap_0767(self):
        r = tranche.run(767, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREVENTIVE_MAINTENANCE_ENGINE')
        self.assertEqual(r["kind"], 'MAINTENANCE_ENGINE')
        self.assertEqual(r["binding"], 'preventive_maintenance_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(767, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(767, {"canonical_name": "OTHER"})
    def test_cap_0768(self):
        r = tranche.run(768, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CORRECTIVE_MAINTENANCE_ENGINE')
        self.assertEqual(r["kind"], 'MAINTENANCE_ENGINE')
        self.assertEqual(r["binding"], 'corrective_maintenance_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(768, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(768, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
