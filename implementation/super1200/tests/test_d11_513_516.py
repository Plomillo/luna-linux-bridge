#!/usr/bin/env python3
"""Negative tests for D11 513-516. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_513_516 as tranche


class D11Tranche513516Tests(unittest.TestCase):
    def test_cap_0513(self):
        r = tranche.run(513, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INDEPENDENT_REPLICATION')
        self.assertEqual(r["kind"], 'G23_SUPPORT_ENGINE')
        self.assertEqual(r["binding"], 'independent_replication')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(513, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(513, {"canonical_name": "OTHER"})
    def test_cap_0514(self):
        r = tranche.run(514, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LITERATURE_REVIEW_ENGINE')
        self.assertEqual(r["kind"], 'RESEARCH_ENGINE')
        self.assertEqual(r["binding"], 'literature_review_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(514, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(514, {"canonical_name": "OTHER"})
    def test_cap_0515(self):
        r = tranche.run(515, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SYSTEMATIC_REVIEW_ENGINE')
        self.assertEqual(r["kind"], 'RESEARCH_ENGINE')
        self.assertEqual(r["binding"], 'systematic_review_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(515, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(515, {"canonical_name": "OTHER"})
    def test_cap_0516(self):
        r = tranche.run(516, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'META_ANALYSIS_ENGINE')
        self.assertEqual(r["kind"], 'STATISTICAL_ENGINE')
        self.assertEqual(r["binding"], 'meta_analysis_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(516, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(516, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
