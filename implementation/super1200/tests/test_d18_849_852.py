#!/usr/bin/env python3
"""Negative tests for D18 849-852. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_849_852 as tranche


class D18Tranche849852Tests(unittest.TestCase):
    def test_cap_0849(self):
        r = tranche.run(849, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'KNOWN_GOOD_GENERATION_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'known_good_generation_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(849, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(849, {"canonical_name": "OTHER"})
    def test_cap_0850(self):
        r = tranche.run(850, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GENERATION_SWITCH_ENGINE')
        self.assertEqual(r["kind"], 'RECOVERY_ENGINE')
        self.assertEqual(r["binding"], 'generation_switch_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(850, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(850, {"canonical_name": "OTHER"})
    def test_cap_0851(self):
        r = tranche.run(851, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SAFE_GARBAGE_COLLECTION')
        self.assertEqual(r["kind"], 'STORAGE_ENGINE')
        self.assertEqual(r["binding"], 'safe_garbage_collection')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(851, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(851, {"canonical_name": "OTHER"})
    def test_cap_0852(self):
        r = tranche.run(852, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ROLLBACK_ROOT_PROTECTION')
        self.assertEqual(r["kind"], 'SAFETY_GATE')
        self.assertEqual(r["binding"], 'rollback_root_protection')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(852, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(852, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
