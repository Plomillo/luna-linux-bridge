#!/usr/bin/env python3
"""Negative tests for D09 385-388. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_385_388 as tranche


class D09Tranche385388Tests(unittest.TestCase):
    def test_cap_0385(self):
        r = tranche.run(385, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'APK_BUILD_ENGINE')
        self.assertEqual(r["kind"], 'BUILD_ENGINE')
        self.assertEqual(r["binding"], 'apk_build_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(385, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(385, {"canonical_name": "OTHER"})
    def test_cap_0386(self):
        r = tranche.run(386, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AAB_BUILD_ENGINE')
        self.assertEqual(r["kind"], 'BUILD_ENGINE')
        self.assertEqual(r["binding"], 'aab_build_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(386, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(386, {"canonical_name": "OTHER"})
    def test_cap_0387(self):
        r = tranche.run(387, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'APK_SIGNATURE_ENGINE')
        self.assertEqual(r["kind"], 'SIGNING_ENGINE')
        self.assertEqual(r["binding"], 'apk_signature_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(387, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(387, {"canonical_name": "OTHER"})
    def test_cap_0388(self):
        r = tranche.run(388, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANDROID_TEST_LAB')
        self.assertEqual(r["kind"], 'LAB')
        self.assertEqual(r["binding"], 'android_test_lab')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(388, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(388, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
