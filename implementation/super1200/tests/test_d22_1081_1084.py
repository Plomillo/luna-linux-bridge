#!/usr/bin/env python3
"""Negative tests for D22 1081-1084. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1081_1084 as tranche


class D22Tranche10811084Tests(unittest.TestCase):
    def test_cap_1081(self):
        r = tranche.run(1081, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_LIFECYCLE_FABRIC')
        self.assertEqual(r["kind"], 'DEFENSIVE_SECURITY_FABRIC')
        self.assertEqual(r["binding"], 'threat_lifecycle_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1081, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1081, {"canonical_name": "OTHER"})
    def test_cap_1082(self):
        r = tranche.run(1082, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_NECESSITY_ENGINE')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'quarantine_necessity_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1082, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1082, {"canonical_name": "OTHER"})
    def test_cap_1083(self):
        r = tranche.run(1083, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_RISK_SCORER')
        self.assertEqual(r["kind"], 'RISK_ENGINE')
        self.assertEqual(r["binding"], 'quarantine_risk_scorer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1083, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1083, {"canonical_name": "OTHER"})
    def test_cap_1084(self):
        r = tranche.run(1084, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_RETENTION_POLICY')
        self.assertEqual(r["kind"], 'POLICY')
        self.assertEqual(r["binding"], 'quarantine_retention_policy')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1084, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1084, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
