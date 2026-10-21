#!/usr/bin/env python3
"""Negative tests for D09 417-420. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_417_420 as tranche


class D09Tranche417420Tests(unittest.TestCase):
    def test_cap_0417(self):
        r = tranche.run(417, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UEFI_PROVIDER')
        self.assertEqual(r["kind"], 'PLATFORM_STANDARD_PROVIDER')
        self.assertEqual(r["binding"], 'uefi_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(417, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(417, {"canonical_name": "OTHER"})
    def test_cap_0418(self):
        r = tranche.run(418, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURE_BOOT_PROVIDER')
        self.assertEqual(r["kind"], 'SECURITY_PROVIDER')
        self.assertEqual(r["binding"], 'secure_boot_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(418, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(418, {"canonical_name": "OTHER"})
    def test_cap_0419(self):
        r = tranche.run(419, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OS_INSTALLER_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'os_installer_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(419, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(419, {"canonical_name": "OTHER"})
    def test_cap_0420(self):
        r = tranche.run(420, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OS_UPDATE_FRAMEWORK')
        self.assertEqual(r["kind"], 'UPDATE_FABRIC')
        self.assertEqual(r["binding"], 'os_update_framework')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(420, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(420, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
