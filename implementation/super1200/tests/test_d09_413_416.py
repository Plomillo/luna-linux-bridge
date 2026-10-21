#!/usr/bin/env python3
"""Negative tests for D09 413-416. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_413_416 as tranche


class D09Tranche413416Tests(unittest.TestCase):
    def test_cap_0413(self):
        r = tranche.run(413, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'APT_REPOSITORY_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_PACKAGE_MANAGER_PROVIDER')
        self.assertEqual(r["binding"], 'apt_repository_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(413, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(413, {"canonical_name": "OTHER"})
    def test_cap_0414(self):
        r = tranche.run(414, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FILESYSTEM_LAYOUT_ENGINE')
        self.assertEqual(r["kind"], 'OS_ENGINE')
        self.assertEqual(r["binding"], 'filesystem_layout_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(414, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(414, {"canonical_name": "OTHER"})
    def test_cap_0415(self):
        r = tranche.run(415, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BOOTLOADER_ENGINE')
        self.assertEqual(r["kind"], 'BOOT_ENGINE')
        self.assertEqual(r["binding"], 'bootloader_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(415, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(415, {"canonical_name": "OTHER"})
    def test_cap_0416(self):
        r = tranche.run(416, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GRUB_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_OS_COMPONENT')
        self.assertEqual(r["binding"], 'grub_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(416, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(416, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
