#!/usr/bin/env python3
"""Negative tests for D08 325-328. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_325_328 as tranche


class D08Tranche325328Tests(unittest.TestCase):
    def test_cap_0325(self):
        r = tranche.run(325, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PALEOGRAPHY_PROVIDER')
        self.assertEqual(r["kind"], 'PROVIDER_INTERFACE')
        self.assertEqual(r["binding"], 'paleography_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(325, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(325, {"canonical_name": "OTHER"})
    def test_cap_0326(self):
        r = tranche.run(326, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CHRONOLOGY_ENGINE')
        self.assertEqual(r["kind"], 'DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'chronology_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(326, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(326, {"canonical_name": "OTHER"})
    def test_cap_0327(self):
        r = tranche.run(327, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GEOGRAPHICAL_CONTEXT_ENGINE')
        self.assertEqual(r["kind"], 'DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'geographical_context_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(327, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(327, {"canonical_name": "OTHER"})
    def test_cap_0328(self):
        r = tranche.run(328, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARCHAEOLOGICAL_EVIDENCE_ADAPTER')
        self.assertEqual(r["kind"], 'DOMAIN_ADAPTER')
        self.assertEqual(r["binding"], 'archaeological_evidence_adapter')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(328, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(328, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
