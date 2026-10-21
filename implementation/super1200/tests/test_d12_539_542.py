#!/usr/bin/env python3
"""Negative tests for D12 539-542. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_539_542 as tranche


class D12Tranche539542Tests(unittest.TestCase):
    def test_cap_0539(self):
        r = tranche.run(539, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CORRUPTION_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'corruption_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(539, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(539, {"canonical_name": "OTHER"})
    def test_cap_0540(self):
        r = tranche.run(540, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CERTIFICATE_EXPIRY_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'certificate_expiry_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(540, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(540, {"canonical_name": "OTHER"})
    def test_cap_0541(self):
        r = tranche.run(541, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REBOOT_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR/TEST')
        self.assertEqual(r["binding"], 'reboot_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(541, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(541, {"canonical_name": "OTHER"})
    def test_cap_0542(self):
        r = tranche.run(542, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'POWER_LOSS_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'power_loss_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(542, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(542, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
