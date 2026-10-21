#!/usr/bin/env python3
"""Negative tests for D09 381-384. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_381_384 as tranche


class D09Tranche381384Tests(unittest.TestCase):
    def test_cap_0381(self):
        r = tranche.run(381, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'JAVA_ANDROID_PROVIDER')
        self.assertEqual(r["kind"], 'PROGRAMMING_LANGUAGE_TOOLCHAIN')
        self.assertEqual(r["binding"], 'java_android_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(381, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(381, {"canonical_name": "OTHER"})
    def test_cap_0382(self):
        r = tranche.run(382, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RUST_ANDROID_PROVIDER')
        self.assertEqual(r["kind"], 'PROGRAMMING_LANGUAGE_TOOLCHAIN')
        self.assertEqual(r["binding"], 'rust_android_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(382, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(382, {"canonical_name": "OTHER"})
    def test_cap_0383(self):
        r = tranche.run(383, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CROSS_COMPILE_ARM64')
        self.assertEqual(r["kind"], 'TOOLCHAIN_CAPABILITY')
        self.assertEqual(r["binding"], 'cross_compile_arm64')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(383, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(383, {"canonical_name": "OTHER"})
    def test_cap_0384(self):
        r = tranche.run(384, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CROSS_COMPILE_ARMV7')
        self.assertEqual(r["kind"], 'TOOLCHAIN_CAPABILITY')
        self.assertEqual(r["binding"], 'cross_compile_armv7')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(384, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(384, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
