#!/usr/bin/env python3
"""Negative tests for D19 905-908. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_905_908 as tranche


class D19Tranche905908Tests(unittest.TestCase):
    def test_cap_0905(self):
        r = tranche.run(905, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'VULNERABILITY_APPLICABILITY_ENGINE')
        self.assertEqual(r["kind"], 'SECURITY_ANALYZER')
        self.assertEqual(r["binding"], 'vulnerability_applicability_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(905, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(905, {"canonical_name": "OTHER"})
    def test_cap_0906(self):
        r = tranche.run(906, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REACHABILITY_SECURITY_ANALYZER')
        self.assertEqual(r["kind"], 'SECURITY_ANALYZER')
        self.assertEqual(r["binding"], 'reachability_security_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(906, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(906, {"canonical_name": "OTHER"})
    def test_cap_0907(self):
        r = tranche.run(907, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPLOITABILITY_CONTEXT_ENGINE')
        self.assertEqual(r["kind"], 'RISK_ENGINE')
        self.assertEqual(r["binding"], 'exploitability_context_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(907, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(907, {"canonical_name": "OTHER"})
    def test_cap_0908(self):
        r = tranche.run(908, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'VULNERABILITY_PRIORITY_ENGINE')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'vulnerability_priority_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(908, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(908, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
