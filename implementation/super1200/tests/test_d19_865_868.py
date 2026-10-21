#!/usr/bin/env python3
"""Negative tests for D19 865-868. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_865_868 as tranche


class D19Tranche865868Tests(unittest.TestCase):
    def test_cap_0865(self):
        r = tranche.run(865, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_ANALYST')
        self.assertEqual(r["kind"], 'SECURITY_ENGINE')
        self.assertEqual(r["binding"], 'security_analyst')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(865, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(865, {"canonical_name": "OTHER"})
    def test_cap_0866(self):
        r = tranche.run(866, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_RECOMMENDER')
        self.assertEqual(r["kind"], 'SECURITY_ENGINE')
        self.assertEqual(r["binding"], 'security_recommender')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(866, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(866, {"canonical_name": "OTHER"})
    def test_cap_0867(self):
        r = tranche.run(867, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_EXECUTOR_BOUNDARY')
        self.assertEqual(r["kind"], 'AUTHORITY_BOUNDARY')
        self.assertEqual(r["binding"], 'security_executor_boundary')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(867, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(867, {"canonical_name": "OTHER"})
    def test_cap_0868(self):
        r = tranche.run(868, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_AUTHORIZATION_GATE')
        self.assertEqual(r["kind"], 'AUTHORIZATION_GATE')
        self.assertEqual(r["binding"], 'security_authorization_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(868, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(868, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
