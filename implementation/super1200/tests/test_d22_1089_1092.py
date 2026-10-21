#!/usr/bin/env python3
"""Negative tests for D22 1089-1092. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1089_1092 as tranche


class D22Tranche10891092Tests(unittest.TestCase):
    def test_cap_1089(self):
        r = tranche.run(1089, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_FINGERPRINT')
        self.assertEqual(r["kind"], 'IDENTITY_ARTIFACT')
        self.assertEqual(r["binding"], 'threat_fingerprint')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1089, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1089, {"canonical_name": "OTHER"})
    def test_cap_1090(self):
        r = tranche.run(1090, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_LINEAGE_RECORD')
        self.assertEqual(r["kind"], 'KNOWLEDGE_RECORD')
        self.assertEqual(r["binding"], 'threat_lineage_record')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1090, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1090, {"canonical_name": "OTHER"})
    def test_cap_1091(self):
        r = tranche.run(1091, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_ESCAPE_ASSUMPTION_TEST')
        self.assertEqual(r["kind"], 'SECURITY_TEST')
        self.assertEqual(r["binding"], 'quarantine_escape_assumption_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1091, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1091, {"canonical_name": "OTHER"})
    def test_cap_1092(self):
        r = tranche.run(1092, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_BOUNDARY_TEST')
        self.assertEqual(r["kind"], 'SECURITY_TEST')
        self.assertEqual(r["binding"], 'quarantine_boundary_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1092, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1092, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
