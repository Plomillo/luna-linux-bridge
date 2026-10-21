#!/usr/bin/env python3
"""Negative tests for D20 969-972. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d20_969_972 as tranche


class D20Tranche969972Tests(unittest.TestCase):
    def test_cap_0969(self):
        r = tranche.run(969, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_CHAIN_OF_CUSTODY')
        self.assertEqual(r["kind"], 'AUDIT_LEDGER')
        self.assertEqual(r["binding"], 'quarantine_chain_of_custody')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(969, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(969, {"canonical_name": "OTHER"})
    def test_cap_0970(self):
        r = tranche.run(970, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_EXPIRATION_POLICY')
        self.assertEqual(r["kind"], 'POLICY')
        self.assertEqual(r["binding"], 'quarantine_expiration_policy')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(970, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(970, {"canonical_name": "OTHER"})
    def test_cap_0971(self):
        r = tranche.run(971, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SAFE_SAMPLE_REPRESENTATION')
        self.assertEqual(r["kind"], 'SECURITY_ARTIFACT')
        self.assertEqual(r["binding"], 'safe_sample_representation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(971, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(971, {"canonical_name": "OTHER"})
    def test_cap_0972(self):
        r = tranche.run(972, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FORENSIC_ANALYSIS_FABRIC')
        self.assertEqual(r["kind"], 'DEFENSIVE_FORENSIC_FABRIC')
        self.assertEqual(r["binding"], 'forensic_analysis_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(972, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(972, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
