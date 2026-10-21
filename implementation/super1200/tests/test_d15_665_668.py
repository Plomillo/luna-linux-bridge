#!/usr/bin/env python3
"""Negative tests for D15 665-668. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d15_665_668 as tranche


class D15Tranche665668Tests(unittest.TestCase):
    def test_cap_0665(self):
        r = tranche.run(665, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BATTERY_DEGRADATION_MODEL')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_MODEL')
        self.assertEqual(r["binding"], 'battery_degradation_model')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(665, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(665, {"canonical_name": "OTHER"})
    def test_cap_0666(self):
        r = tranche.run(666, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'POWER_MANAGEMENT_DIAGNOSTICS')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'power_management_diagnostics')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(666, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(666, {"canonical_name": "OTHER"})
    def test_cap_0667(self):
        r = tranche.run(667, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THERMAL_DIAGNOSTICS')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'thermal_diagnostics')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(667, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(667, {"canonical_name": "OTHER"})
    def test_cap_0668(self):
        r = tranche.run(668, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CPU_HEALTH_DIAGNOSTICS')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'cpu_health_diagnostics')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(668, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(668, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
