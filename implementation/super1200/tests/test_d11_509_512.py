#!/usr/bin/env python3
"""Negative tests for D11 509-512. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_509_512 as tranche


class D11Tranche509512Tests(unittest.TestCase):
    def test_cap_0509(self):
        r = tranche.run(509, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOURCE_DIVERSIFICATION')
        self.assertEqual(r["kind"], 'RESEARCH_POLICY')
        self.assertEqual(r["binding"], 'source_diversification')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(509, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(509, {"canonical_name": "OTHER"})
    def test_cap_0510(self):
        r = tranche.run(510, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ADVERSARIAL_RESEARCH')
        self.assertEqual(r["kind"], 'RESEARCH_ENGINE')
        self.assertEqual(r["binding"], 'adversarial_research')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(510, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(510, {"canonical_name": "OTHER"})
    def test_cap_0511(self):
        r = tranche.run(511, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COUNTEREVIDENCE_SEARCH')
        self.assertEqual(r["kind"], 'RESEARCH_ENGINE')
        self.assertEqual(r["binding"], 'counterevidence_search')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(511, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(511, {"canonical_name": "OTHER"})
    def test_cap_0512(self):
        r = tranche.run(512, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REPLICATION_ENGINE')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'replication_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(512, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(512, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
