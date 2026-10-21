#!/usr/bin/env python3
"""Negative tests for D08 341-344. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_341_344 as tranche


class D08Tranche341344Tests(unittest.TestCase):
    def test_cap_0341(self):
        r = tranche.run(341, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ZPAQ_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_BINARY_TOOL')
        self.assertEqual(r["binding"], 'zpaq_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(341, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(341, {"canonical_name": "OTHER"})
    def test_cap_0342(self):
        r = tranche.run(342, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LONG_RANGE_COMPRESSION_PROVIDER')
        self.assertEqual(r["kind"], 'PROVIDER_INTERFACE')
        self.assertEqual(r["binding"], 'long_range_compression_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(342, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(342, {"canonical_name": "OTHER"})
    def test_cap_0343(self):
        r = tranche.run(343, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DOMAIN_SPECIFIC_COMPRESSOR')
        self.assertEqual(r["kind"], 'COMPRESSION_ENGINE')
        self.assertEqual(r["binding"], 'domain_specific_compressor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(343, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(343, {"canonical_name": "OTHER"})
    def test_cap_0344(self):
        r = tranche.run(344, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MODEL_WEIGHT_COMPRESSION')
        self.assertEqual(r["kind"], 'DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'model_weight_compression')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(344, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(344, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
