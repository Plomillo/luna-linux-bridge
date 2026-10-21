#!/usr/bin/env python3
"""Negative tests for D15 661-664. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d15_661_664 as tranche


class D15Tranche661664Tests(unittest.TestCase):
    def test_cap_0661(self):
        r = tranche.run(661, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MACHINE_HEALTH_FABRIC')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_FABRIC')
        self.assertEqual(r["binding"], 'machine_health_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(661, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(661, {"canonical_name": "OTHER"})
    def test_cap_0662(self):
        r = tranche.run(662, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HARDWARE_INVENTORY_ENGINE')
        self.assertEqual(r["kind"], 'DISCOVERY_ENGINE')
        self.assertEqual(r["binding"], 'hardware_inventory_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(662, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(662, {"canonical_name": "OTHER"})
    def test_cap_0663(self):
        r = tranche.run(663, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SENSOR_TELEMETRY_ENGINE')
        self.assertEqual(r["kind"], 'OBSERVABILITY_ENGINE')
        self.assertEqual(r["binding"], 'sensor_telemetry_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(663, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(663, {"canonical_name": "OTHER"})
    def test_cap_0664(self):
        r = tranche.run(664, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BATTERY_HEALTH_ENGINE')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'battery_health_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(664, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(664, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
