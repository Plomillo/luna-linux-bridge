#!/usr/bin/env python3
"""Negative tests for D08 321-324. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_321_324 as tranche


class D08Tranche321324Tests(unittest.TestCase):
    def test_cap_0321(self):
        r = tranche.run(321, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECONDARY_SOURCE_REGISTRY')
        self.assertEqual(r["kind"], 'SOURCE_REGISTRY')
        self.assertEqual(r["binding"], 'secondary_source_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(321, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(321, {"canonical_name": "OTHER"})
    def test_cap_0322(self):
        r = tranche.run(322, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MANUSCRIPT_REGISTRY')
        self.assertEqual(r["kind"], 'DOMAIN_REGISTRY')
        self.assertEqual(r["binding"], 'manuscript_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(322, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(322, {"canonical_name": "OTHER"})
    def test_cap_0323(self):
        r = tranche.run(323, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TEXTUAL_VARIANT_ENGINE')
        self.assertEqual(r["kind"], 'DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'textual_variant_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(323, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(323, {"canonical_name": "OTHER"})
    def test_cap_0324(self):
        r = tranche.run(324, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STEMMATIC_ANALYSIS')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'stemmatic_analysis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(324, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(324, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
