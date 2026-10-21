#!/usr/bin/env python3
"""Negative tests for D11 521-524. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_521_524 as tranche


class D11Tranche521524Tests(unittest.TestCase):
    def test_cap_0521(self):
        r = tranche.run(521, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONCEPT_ALIGNMENT')
        self.assertEqual(r["kind"], 'SEMANTIC_ENGINE')
        self.assertEqual(r["binding"], 'concept_alignment')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(521, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(521, {"canonical_name": "OTHER"})
    def test_cap_0522(self):
        r = tranche.run(522, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TERMINOLOGY_DISAMBIGUATOR')
        self.assertEqual(r["kind"], 'SEMANTIC_ENGINE')
        self.assertEqual(r["binding"], 'terminology_disambiguator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(522, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(522, {"canonical_name": "OTHER"})
    def test_cap_0523(self):
        r = tranche.run(523, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EPISTEMIC_BOUNDARY_ENGINE')
        self.assertEqual(r["kind"], 'GOVERNANCE_ENGINE')
        self.assertEqual(r["binding"], 'epistemic_boundary_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(523, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(523, {"canonical_name": "OTHER"})
    def test_cap_0524(self):
        r = tranche.run(524, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'METHODOLOGICAL_COMPATIBILITY_ENGINE')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'methodological_compatibility_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(524, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(524, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
