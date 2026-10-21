#!/usr/bin/env python3
"""Negative tests for D22 1117-1120. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1117_1120 as tranche


class D22Tranche11171120Tests(unittest.TestCase):
    def test_cap_1117(self):
        r = tranche.run(1117, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_DISPOSITION_ENGINE')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'threat_disposition_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1117, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1117, {"canonical_name": "OTHER"})
    def test_cap_1118(self):
        r = tranche.run(1118, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DISPOSITION_INDEPENDENT_VALIDATION')
        self.assertEqual(r["kind"], 'G23_INTERFACE')
        self.assertEqual(r["binding"], 'disposition_independent_validation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1118, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1118, {"canonical_name": "OTHER"})
    def test_cap_1119(self):
        r = tranche.run(1119, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_LIFECYCLE_AUDIT')
        self.assertEqual(r["kind"], 'AUDIT_ENGINE')
        self.assertEqual(r["binding"], 'threat_lifecycle_audit')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1119, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1119, {"canonical_name": "OTHER"})
    def test_cap_1120(self):
        r = tranche.run(1120, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ZERO_UNNECESSARY_LIVE_MALWARE_GATE')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'zero_unnecessary_live_malware_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1120, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1120, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
