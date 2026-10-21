#!/usr/bin/env python3
"""Negative tests for D18 797-800. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_797_800 as tranche


class D18Tranche797800Tests(unittest.TestCase):
    def test_cap_0797(self):
        r = tranche.run(797, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SCHEMA_DIFF_ENGINE')
        self.assertEqual(r["kind"], 'DIFF_ENGINE')
        self.assertEqual(r["binding"], 'schema_diff_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(797, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(797, {"canonical_name": "OTHER"})
    def test_cap_0798(self):
        r = tranche.run(798, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PERFORMANCE_DIFF_ENGINE')
        self.assertEqual(r["kind"], 'DIFF_ENGINE')
        self.assertEqual(r["binding"], 'performance_diff_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(798, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(798, {"canonical_name": "OTHER"})
    def test_cap_0799(self):
        r = tranche.run(799, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_DIFF_ENGINE')
        self.assertEqual(r["kind"], 'DIFF_ENGINE')
        self.assertEqual(r["binding"], 'security_diff_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(799, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(799, {"canonical_name": "OTHER"})
    def test_cap_0800(self):
        r = tranche.run(800, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CHANGE_RECEIPT')
        self.assertEqual(r["kind"], 'RECEIPT')
        self.assertEqual(r["binding"], 'change_receipt')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(800, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(800, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
