#!/usr/bin/env python3
"""Negative tests for D09 409-412. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_409_412 as tranche


class D09Tranche409412Tests(unittest.TestCase):
    def test_cap_0409(self):
        r = tranche.run(409, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'YOCTO_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_OS_BUILD_TOOLCHAIN')
        self.assertEqual(r["binding"], 'yocto_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(409, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(409, {"canonical_name": "OTHER"})
    def test_cap_0410(self):
        r = tranche.run(410, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEBIAN_IMAGE_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_OS_DISTRIBUTION_PROVIDER')
        self.assertEqual(r["binding"], 'debian_image_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(410, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(410, {"canonical_name": "OTHER"})
    def test_cap_0411(self):
        r = tranche.run(411, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PACKAGE_REPOSITORY_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'package_repository_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(411, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(411, {"canonical_name": "OTHER"})
    def test_cap_0412(self):
        r = tranche.run(412, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PACKAGE_SIGNING')
        self.assertEqual(r["kind"], 'SIGNING_ENGINE')
        self.assertEqual(r["binding"], 'package_signing')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(412, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(412, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
