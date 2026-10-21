#!/usr/bin/env python3
"""Negative tests for D18 809-812. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_809_812 as tranche


class D18Tranche809812Tests(unittest.TestCase):
    def test_cap_0809(self):
        r = tranche.run(809, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEPRECATION_IMPACT_ANALYZER')
        self.assertEqual(r["kind"], 'IMPACT_ENGINE')
        self.assertEqual(r["binding"], 'deprecation_impact_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(809, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(809, {"canonical_name": "OTHER"})
    def test_cap_0810(self):
        r = tranche.run(810, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEPRECATION_MIGRATION_ASSISTANT')
        self.assertEqual(r["kind"], 'MIGRATION_PLANNER')
        self.assertEqual(r["binding"], 'deprecation_migration_assistant')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(810, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(810, {"canonical_name": "OTHER"})
    def test_cap_0811(self):
        r = tranche.run(811, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LEGACY_COMPATIBILITY_LAYER')
        self.assertEqual(r["kind"], 'COMPATIBILITY_LAYER')
        self.assertEqual(r["binding"], 'legacy_compatibility_layer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(811, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(811, {"canonical_name": "OTHER"})
    def test_cap_0812(self):
        r = tranche.run(812, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPATIBILITY_SHIM_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'compatibility_shim_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(812, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(812, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
