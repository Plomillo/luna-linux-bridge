#!/usr/bin/env python3
"""Negative tests for D19 913-916. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_913_916 as tranche


class D19Tranche913916Tests(unittest.TestCase):
    def test_cap_0913(self):
        r = tranche.run(913, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SBOM_SECURITY_ANALYZER')
        self.assertEqual(r["kind"], 'SECURITY_ANALYZER')
        self.assertEqual(r["binding"], 'sbom_security_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(913, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(913, {"canonical_name": "OTHER"})
    def test_cap_0914(self):
        r = tranche.run(914, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEPENDENCY_VULNERABILITY_ENGINE')
        self.assertEqual(r["kind"], 'SECURITY_ANALYZER')
        self.assertEqual(r["binding"], 'dependency_vulnerability_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(914, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(914, {"canonical_name": "OTHER"})
    def test_cap_0915(self):
        r = tranche.run(915, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALICIOUS_DEPENDENCY_DETECTOR')
        self.assertEqual(r["kind"], 'SUPPLY_CHAIN_DETECTOR')
        self.assertEqual(r["binding"], 'malicious_dependency_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(915, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(915, {"canonical_name": "OTHER"})
    def test_cap_0916(self):
        r = tranche.run(916, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TYPOSQUATTING_DETECTOR')
        self.assertEqual(r["kind"], 'SUPPLY_CHAIN_DETECTOR')
        self.assertEqual(r["binding"], 'typosquatting_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(916, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(916, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
