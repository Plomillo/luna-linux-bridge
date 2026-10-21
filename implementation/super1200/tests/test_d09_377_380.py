#!/usr/bin/env python3
"""Negative tests for D09 377-380. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_377_380 as tranche


class D09Tranche377380Tests(unittest.TestCase):
    def test_cap_0377(self):
        r = tranche.run(377, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANDROID_PLATFORM_FABRIC')
        self.assertEqual(r["kind"], 'PLATFORM_FABRIC')
        self.assertEqual(r["binding"], 'android_platform_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(377, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(377, {"canonical_name": "OTHER"})
    def test_cap_0378(self):
        r = tranche.run(378, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANDROID_SDK_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_PLATFORM_TOOLCHAIN')
        self.assertEqual(r["binding"], 'android_sdk_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(378, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(378, {"canonical_name": "OTHER"})
    def test_cap_0379(self):
        r = tranche.run(379, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANDROID_NDK_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_PLATFORM_TOOLCHAIN')
        self.assertEqual(r["binding"], 'android_ndk_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(379, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(379, {"canonical_name": "OTHER"})
    def test_cap_0380(self):
        r = tranche.run(380, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'KOTLIN_PROVIDER')
        self.assertEqual(r["kind"], 'PROGRAMMING_LANGUAGE_TOOLCHAIN')
        self.assertEqual(r["binding"], 'kotlin_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(380, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(380, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
