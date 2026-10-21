#!/usr/bin/env python3
"""Negative tests for D22 1101-1104. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1101_1104 as tranche


class D22Tranche11011104Tests(unittest.TestCase):
    def test_cap_1101(self):
        r = tranche.run(1101, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SAMPLE_RELEASE_PROHIBITION')
        self.assertEqual(r["kind"], 'SECURITY_POLICY')
        self.assertEqual(r["binding"], 'sample_release_prohibition')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1101, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1101, {"canonical_name": "OTHER"})
    def test_cap_1102(self):
        r = tranche.run(1102, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_DESTRUCTION_GATE')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'threat_destruction_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1102, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1102, {"canonical_name": "OTHER"})
    def test_cap_1103(self):
        r = tranche.run(1103, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_DESTRUCTION_AUTHORIZATION')
        self.assertEqual(r["kind"], 'AUTHORIZATION_CONTROL')
        self.assertEqual(r["binding"], 'threat_destruction_authorization')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1103, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1103, {"canonical_name": "OTHER"})
    def test_cap_1104(self):
        r = tranche.run(1104, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURE_SAMPLE_DISPOSAL')
        self.assertEqual(r["kind"], 'REMEDIATION_ENGINE')
        self.assertEqual(r["binding"], 'secure_sample_disposal')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1104, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1104, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
