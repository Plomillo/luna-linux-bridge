#!/usr/bin/env python3
"""Negative tests for D19 869-872. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_869_872 as tranche


class D19Tranche869872Tests(unittest.TestCase):
    def test_cap_0869(self):
        r = tranche.run(869, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_EVIDENCE_LEDGER')
        self.assertEqual(r["kind"], 'LEDGER')
        self.assertEqual(r["binding"], 'security_evidence_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(869, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(869, {"canonical_name": "OTHER"})
    def test_cap_0870(self):
        r = tranche.run(870, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_FINDING_IDENTITY')
        self.assertEqual(r["kind"], 'IDENTITY_PRIMITIVE')
        self.assertEqual(r["binding"], 'security_finding_identity')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(870, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(870, {"canonical_name": "OTHER"})
    def test_cap_0871(self):
        r = tranche.run(871, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_CONFIDENCE_ENGINE')
        self.assertEqual(r["kind"], 'EPISTEMIC_ENGINE')
        self.assertEqual(r["binding"], 'security_confidence_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(871, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(871, {"canonical_name": "OTHER"})
    def test_cap_0872(self):
        r = tranche.run(872, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_UNCERTAINTY_ADAPTER')
        self.assertEqual(r["kind"], 'ADAPTER')
        self.assertEqual(r["binding"], 'security_uncertainty_adapter')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(872, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(872, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
