#!/usr/bin/env python3
"""Negative tests for D09 421-424. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_421_424 as tranche


class D09Tranche421424Tests(unittest.TestCase):
    def test_cap_0421(self):
        r = tranche.run(421, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AB_UPDATE_PROVIDER')
        self.assertEqual(r["kind"], 'UPDATE_PROVIDER')
        self.assertEqual(r["binding"], 'ab_update_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(421, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(421, {"canonical_name": "OTHER"})
    def test_cap_0422(self):
        r = tranche.run(422, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RECOVERY_IMAGE_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'recovery_image_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(422, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(422, {"canonical_name": "OTHER"})
    def test_cap_0423(self):
        r = tranche.run(423, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HARDWARE_ABSTRACTION_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'hardware_abstraction_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(423, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(423, {"canonical_name": "OTHER"})
    def test_cap_0424(self):
        r = tranche.run(424, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEVICE_TREE_PROVIDER')
        self.assertEqual(r["kind"], 'OS_COMPONENT_PROVIDER')
        self.assertEqual(r["binding"], 'device_tree_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(424, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(424, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
