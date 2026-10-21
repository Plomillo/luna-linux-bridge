#!/usr/bin/env python3
"""Negative tests for D19 925-928. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_925_928 as tranche


class D19Tranche925928Tests(unittest.TestCase):
    def test_cap_0925(self):
        r = tranche.run(925, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CRITICAL_FILE_PROTECTION')
        self.assertEqual(r["kind"], 'SECURITY_POLICY')
        self.assertEqual(r["binding"], 'critical_file_protection')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(925, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(925, {"canonical_name": "OTHER"})
    def test_cap_0926(self):
        r = tranche.run(926, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PRIVILEGE_ESCALATION_MONITOR')
        self.assertEqual(r["kind"], 'MONITOR')
        self.assertEqual(r["binding"], 'privilege_escalation_monitor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(926, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(926, {"canonical_name": "OTHER"})
    def test_cap_0927(self):
        r = tranche.run(927, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_EVENT_CORRELATOR')
        self.assertEqual(r["kind"], 'CORRELATION_ENGINE')
        self.assertEqual(r["binding"], 'security_event_correlator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(927, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(927, {"canonical_name": "OTHER"})
    def test_cap_0928(self):
        r = tranche.run(928, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NETWORK_SECURITY_FABRIC')
        self.assertEqual(r["kind"], 'DEFENSIVE_SECURITY_FABRIC')
        self.assertEqual(r["binding"], 'network_security_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(928, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(928, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
