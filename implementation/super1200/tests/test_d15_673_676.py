#!/usr/bin/env python3
"""Negative tests for D15 673-676. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d15_673_676 as tranche


class D15Tranche673676Tests(unittest.TestCase):
    def test_cap_0673(self):
        r = tranche.run(673, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FIRMWARE_HEALTH_ENGINE')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'firmware_health_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(673, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(673, {"canonical_name": "OTHER"})
    def test_cap_0674(self):
        r = tranche.run(674, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DRIVER_HEALTH_ENGINE')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'driver_health_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(674, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(674, {"canonical_name": "OTHER"})
    def test_cap_0675(self):
        r = tranche.run(675, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'KERNEL_HEALTH_ENGINE')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'kernel_health_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(675, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(675, {"canonical_name": "OTHER"})
    def test_cap_0676(self):
        r = tranche.run(676, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BOOT_HEALTH_ENGINE')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'boot_health_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(676, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(676, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
