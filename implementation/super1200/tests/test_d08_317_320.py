#!/usr/bin/env python3
"""Negative tests for D08 317-320. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_317_320 as tranche


class D08Tranche317320Tests(unittest.TestCase):
    def test_cap_0317(self):
        r = tranche.run(317, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NEGATIVE_RESULT_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'negative_result_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(317, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(317, {"canonical_name": "OTHER"})
    def test_cap_0318(self):
        r = tranche.run(318, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNKNOWN_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'unknown_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(318, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(318, {"canonical_name": "OTHER"})
    def test_cap_0319(self):
        r = tranche.run(319, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HISTORICAL_METHOD_ENGINE')
        self.assertEqual(r["kind"], 'DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'historical_method_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(319, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(319, {"canonical_name": "OTHER"})
    def test_cap_0320(self):
        r = tranche.run(320, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PRIMARY_SOURCE_REGISTRY')
        self.assertEqual(r["kind"], 'SOURCE_REGISTRY')
        self.assertEqual(r["binding"], 'primary_source_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(320, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(320, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
