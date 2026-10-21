#!/usr/bin/env python3
"""Negative tests for D09 389-392. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_389_392 as tranche


class D09Tranche389392Tests(unittest.TestCase):
    def test_cap_0389(self):
        r = tranche.run(389, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EMULATOR_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_PLATFORM_RUNTIME')
        self.assertEqual(r["binding"], 'emulator_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(389, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(389, {"canonical_name": "OTHER"})
    def test_cap_0390(self):
        r = tranche.run(390, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ADB_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_BINARY_TOOL')
        self.assertEqual(r["binding"], 'adb_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(390, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(390, {"canonical_name": "OTHER"})
    def test_cap_0391(self):
        r = tranche.run(391, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEVICE_CAPABILITY_DISCOVERY')
        self.assertEqual(r["kind"], 'DISCOVERY_ENGINE')
        self.assertEqual(r["binding"], 'device_capability_discovery')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(391, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(391, {"canonical_name": "OTHER"})
    def test_cap_0392(self):
        r = tranche.run(392, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANDROID_PERFORMANCE_PROFILER')
        self.assertEqual(r["kind"], 'PROFILER')
        self.assertEqual(r["binding"], 'android_performance_profiler')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(392, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(392, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
