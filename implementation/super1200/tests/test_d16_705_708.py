#!/usr/bin/env python3
"""Negative tests for D16 705-708. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d16_705_708 as tranche


class D16Tranche705708Tests(unittest.TestCase):
    def test_cap_0705(self):
        r = tranche.run(705, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DIRECTX_TRANSLATION_FABRIC')
        self.assertEqual(r["kind"], 'GRAPHICS_FABRIC')
        self.assertEqual(r["binding"], 'directx_translation_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(705, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(705, {"canonical_name": "OTHER"})
    def test_cap_0706(self):
        r = tranche.run(706, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'VULKAN_CAPABILITY_ENGINE')
        self.assertEqual(r["kind"], 'DISCOVERY_ENGINE')
        self.assertEqual(r["binding"], 'vulkan_capability_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(706, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(706, {"canonical_name": "OTHER"})
    def test_cap_0707(self):
        r = tranche.run(707, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MESA_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_SYSTEM_LIBRARY')
        self.assertEqual(r["binding"], 'mesa_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(707, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(707, {"canonical_name": "OTHER"})
    def test_cap_0708(self):
        r = tranche.run(708, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GRAPHICS_DRIVER_MATRIX')
        self.assertEqual(r["kind"], 'COMPATIBILITY_MATRIX')
        self.assertEqual(r["binding"], 'graphics_driver_matrix')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(708, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(708, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
