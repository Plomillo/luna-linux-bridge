#!/usr/bin/env python3
"""Negative tests for D18 853-856. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_853_856 as tranche


class D18Tranche853856Tests(unittest.TestCase):
    def test_cap_0853(self):
        r = tranche.run(853, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STORAGE_PRESSURE_MANAGER')
        self.assertEqual(r["kind"], 'RESOURCE_ENGINE')
        self.assertEqual(r["binding"], 'storage_pressure_manager')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(853, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(853, {"canonical_name": "OTHER"})
    def test_cap_0854(self):
        r = tranche.run(854, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_PARALLELIZER')
        self.assertEqual(r["kind"], 'SCHEDULER')
        self.assertEqual(r["binding"], 'maintenance_parallelizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(854, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(854, {"canonical_name": "OTHER"})
    def test_cap_0855(self):
        r = tranche.run(855, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_CRITICAL_PATH')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'maintenance_critical_path')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(855, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(855, {"canonical_name": "OTHER"})
    def test_cap_0856(self):
        r = tranche.run(856, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TOIL_DETECTOR')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'toil_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(856, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(856, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
