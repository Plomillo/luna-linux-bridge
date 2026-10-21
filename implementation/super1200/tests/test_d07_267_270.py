#!/usr/bin/env python3
"""Negative tests for D07 267-270. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_267_270 as tranche


class D07Tranche267270Tests(unittest.TestCase):
    def test_cap_0267(self):
        r = tranche.run(267, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'JULIA_PROVIDER')
        self.assertEqual(r["kind"], 'PROGRAMMING_LANGUAGE_RUNTIME')
        self.assertEqual(r["binding"], 'julia_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(267, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(267, {"canonical_name": "OTHER"})
    def test_cap_0268(self):
        r = tranche.run(268, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DUCKDB_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_LIBRARY_DATABASE')
        self.assertEqual(r["binding"], 'duckdb_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(268, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(268, {"canonical_name": "OTHER"})
    def test_cap_0269(self):
        r = tranche.run(269, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'APACHE_ARROW_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_LIBRARY_STANDARD')
        self.assertEqual(r["binding"], 'apache_arrow_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(269, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(269, {"canonical_name": "OTHER"})
    def test_cap_0270(self):
        r = tranche.run(270, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'POLARS_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_LIBRARY')
        self.assertEqual(r["binding"], 'polars_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(270, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(270, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
