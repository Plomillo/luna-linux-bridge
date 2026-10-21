#!/usr/bin/env python3
"""Negative tests for D18 793-796. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_793_796 as tranche


class D18Tranche793796Tests(unittest.TestCase):
    def test_cap_0793(self):
        r = tranche.run(793, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONFIGURATION_DIFF_ENGINE')
        self.assertEqual(r["kind"], 'DIFF_ENGINE')
        self.assertEqual(r["binding"], 'configuration_diff_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(793, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(793, {"canonical_name": "OTHER"})
    def test_cap_0794(self):
        r = tranche.run(794, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEPENDENCY_DIFF_ENGINE')
        self.assertEqual(r["kind"], 'DIFF_ENGINE')
        self.assertEqual(r["binding"], 'dependency_diff_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(794, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(794, {"canonical_name": "OTHER"})
    def test_cap_0795(self):
        r = tranche.run(795, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ABI_DIFF_ENGINE')
        self.assertEqual(r["kind"], 'DIFF_ENGINE')
        self.assertEqual(r["binding"], 'abi_diff_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(795, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(795, {"canonical_name": "OTHER"})
    def test_cap_0796(self):
        r = tranche.run(796, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'API_DIFF_ENGINE')
        self.assertEqual(r["kind"], 'DIFF_ENGINE')
        self.assertEqual(r["binding"], 'api_diff_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(796, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(796, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
