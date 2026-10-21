#!/usr/bin/env python3
"""Negative tests for D19 933-936. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_933_936 as tranche


class D19Tranche933936Tests(unittest.TestCase):
    def test_cap_0933(self):
        r = tranche.run(933, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OUTBOUND_CONNECTION_POLICY')
        self.assertEqual(r["kind"], 'SECURITY_POLICY')
        self.assertEqual(r["binding"], 'outbound_connection_policy')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(933, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(933, {"canonical_name": "OTHER"})
    def test_cap_0934(self):
        r = tranche.run(934, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNEXPECTED_EGRESS_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'unexpected_egress_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(934, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(934, {"canonical_name": "OTHER"})
    def test_cap_0935(self):
        r = tranche.run(935, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REPOSITORY_SECURITY_ADVISER')
        self.assertEqual(r["kind"], 'SECURITY_ADVISER')
        self.assertEqual(r["binding"], 'repository_security_adviser')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(935, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(935, {"canonical_name": "OTHER"})
    def test_cap_0936(self):
        r = tranche.run(936, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMMIT_INTEGRITY_ANALYZER')
        self.assertEqual(r["kind"], 'SECURITY_ANALYZER')
        self.assertEqual(r["binding"], 'commit_integrity_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(936, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(936, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
