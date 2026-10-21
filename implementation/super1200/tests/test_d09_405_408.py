#!/usr/bin/env python3
"""Negative tests for D09 405-408. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_405_408 as tranche


class D09Tranche405408Tests(unittest.TestCase):
    def test_cap_0405(self):
        r = tranche.run(405, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SYSTEMD_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_OS_COMPONENT')
        self.assertEqual(r["binding"], 'systemd_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(405, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(405, {"canonical_name": "OTHER"})
    def test_cap_0406(self):
        r = tranche.run(406, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INITRAMFS_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'initramfs_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(406, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(406, {"canonical_name": "OTHER"})
    def test_cap_0407(self):
        r = tranche.run(407, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ROOTFS_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'rootfs_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(407, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(407, {"canonical_name": "OTHER"})
    def test_cap_0408(self):
        r = tranche.run(408, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BUILDROOT_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_OS_BUILD_TOOLCHAIN')
        self.assertEqual(r["binding"], 'buildroot_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(408, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(408, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
