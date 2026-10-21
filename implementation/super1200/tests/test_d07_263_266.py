#!/usr/bin/env python3
"""Negative tests for D07 263-266. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_263_266 as tranche


class D07Tranche263266Tests(unittest.TestCase):
    def test_cap_0263(self):
        r = tranche.run(263, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUANTITATIVE_RESEARCH_FABRIC')
        self.assertEqual(r["kind"], 'RESEARCH_FABRIC')
        self.assertEqual(r["binding"], 'quantitative_research_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(263, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(263, {"canonical_name": "OTHER"})
    def test_cap_0264(self):
        r = tranche.run(264, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STATISTICAL_ENGINE')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'statistical_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(264, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(264, {"canonical_name": "OTHER"})
    def test_cap_0265(self):
        r = tranche.run(265, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'R_PROVIDER')
        self.assertEqual(r["kind"], 'PROGRAMMING_LANGUAGE_RUNTIME')
        self.assertEqual(r["binding"], 'r_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(265, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(265, {"canonical_name": "OTHER"})
    def test_cap_0266(self):
        r = tranche.run(266, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PYTHON_SCIENTIFIC_PROVIDER')
        self.assertEqual(r["kind"], 'PROGRAMMING_LANGUAGE_RUNTIME')
        self.assertEqual(r["binding"], 'python_scientific_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(266, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(266, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
