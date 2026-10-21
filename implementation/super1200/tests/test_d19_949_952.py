#!/usr/bin/env python3
"""Negative tests for D19 949-952. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_949_952 as tranche


class D19Tranche949952Tests(unittest.TestCase):
    def test_cap_0949(self):
        r = tranche.run(949, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_CAPABILITY_BASELINE')
        self.assertEqual(r["kind"], 'BASELINE')
        self.assertEqual(r["binding"], 'luna_defender_capability_baseline')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(949, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(949, {"canonical_name": "OTHER"})
    def test_cap_0950(self):
        r = tranche.run(950, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_CUSTOM_RULE_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'luna_defender_custom_rule_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(950, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(950, {"canonical_name": "OTHER"})
    def test_cap_0951(self):
        r = tranche.run(951, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_RULE_TEST_LAB')
        self.assertEqual(r["kind"], 'LAB')
        self.assertEqual(r["binding"], 'luna_defender_rule_test_lab')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(951, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(951, {"canonical_name": "OTHER"})
    def test_cap_0952(self):
        r = tranche.run(952, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_FALSE_POSITIVE_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'luna_defender_false_positive_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(952, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(952, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
