#!/usr/bin/env python3
"""Negative tests for D20 965-968. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d20_965_968 as tranche


class D20Tranche965968Tests(unittest.TestCase):
    def test_cap_0965(self):
        r = tranche.run(965, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_ACCESS_CONTROL')
        self.assertEqual(r["kind"], 'SECURITY_POLICY')
        self.assertEqual(r["binding"], 'quarantine_access_control')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(965, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(965, {"canonical_name": "OTHER"})
    def test_cap_0966(self):
        r = tranche.run(966, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_NETWORK_ISOLATION')
        self.assertEqual(r["kind"], 'SECURITY_BOUNDARY')
        self.assertEqual(r["binding"], 'quarantine_network_isolation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(966, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(966, {"canonical_name": "OTHER"})
    def test_cap_0967(self):
        r = tranche.run(967, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_EXECUTION_ISOLATION')
        self.assertEqual(r["kind"], 'SECURITY_BOUNDARY')
        self.assertEqual(r["binding"], 'quarantine_execution_isolation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(967, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(967, {"canonical_name": "OTHER"})
    def test_cap_0968(self):
        r = tranche.run(968, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_EVIDENCE_PRESERVATION')
        self.assertEqual(r["kind"], 'EVIDENCE_ENGINE')
        self.assertEqual(r["binding"], 'quarantine_evidence_preservation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(968, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(968, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
