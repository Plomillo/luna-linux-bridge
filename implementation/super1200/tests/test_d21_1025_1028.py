#!/usr/bin/env python3
"""Negative tests for D21 1025-1028. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1025_1028 as tranche


class D21Tranche10251028Tests(unittest.TestCase):
    def test_cap_1025(self):
        r = tranche.run(1025, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALICIOUS_BEHAVIOR_ABSENCE_GATE')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'malicious_behavior_absence_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1025, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1025, {"canonical_name": "OTHER"})
    def test_cap_1026(self):
        r = tranche.run(1026, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RESIDUAL_RISK_ANALYZER')
        self.assertEqual(r["kind"], 'RISK_ENGINE')
        self.assertEqual(r["binding"], 'residual_risk_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1026, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1026, {"canonical_name": "OTHER"})
    def test_cap_1027(self):
        r = tranche.run(1027, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SANITIZED_ARTIFACT_IDENTITY')
        self.assertEqual(r["kind"], 'IDENTITY_PRIMITIVE')
        self.assertEqual(r["binding"], 'sanitized_artifact_identity')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1027, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1027, {"canonical_name": "OTHER"})
    def test_cap_1028(self):
        r = tranche.run(1028, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ORIGINAL_TO_SANITIZED_PROVENANCE')
        self.assertEqual(r["kind"], 'PROVENANCE_RELATION')
        self.assertEqual(r["binding"], 'original_to_sanitized_provenance')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1028, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1028, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
