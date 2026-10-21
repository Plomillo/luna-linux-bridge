#!/usr/bin/env python3
"""Negative tests for D10 462-465. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d10_462_465 as tranche


class D10Tranche462465Tests(unittest.TestCase):
    def test_cap_0462(self):
        r = tranche.run(462, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CAPABILITY_EXTENSION_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'capability_extension_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(462, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(462, {"canonical_name": "OTHER"})
    def test_cap_0463(self):
        r = tranche.run(463, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COGNITIVE_EXTENSION_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'cognitive_extension_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(463, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(463, {"canonical_name": "OTHER"})
    def test_cap_0464(self):
        r = tranche.run(464, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_INTERFACE_GENERATOR')
        self.assertEqual(r["kind"], 'FACTORY_TOOL')
        self.assertEqual(r["binding"], 'engine_interface_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(464, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(464, {"canonical_name": "OTHER"})
    def test_cap_0465(self):
        r = tranche.run(465, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_MANIFEST_GENERATOR')
        self.assertEqual(r["kind"], 'FACTORY_TOOL')
        self.assertEqual(r["binding"], 'engine_manifest_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(465, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(465, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
