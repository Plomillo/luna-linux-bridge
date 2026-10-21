#!/usr/bin/env python3
"""Negative tests for D19 929-932. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_929_932 as tranche


class D19Tranche929932Tests(unittest.TestCase):
    def test_cap_0929(self):
        r = tranche.run(929, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NETWORK_BEHAVIOR_BASELINE')
        self.assertEqual(r["kind"], 'BASELINE')
        self.assertEqual(r["binding"], 'network_behavior_baseline')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(929, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(929, {"canonical_name": "OTHER"})
    def test_cap_0930(self):
        r = tranche.run(930, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NETWORK_ANOMALY_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'network_anomaly_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(930, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(930, {"canonical_name": "OTHER"})
    def test_cap_0931(self):
        r = tranche.run(931, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DNS_SECURITY_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'dns_security_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(931, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(931, {"canonical_name": "OTHER"})
    def test_cap_0932(self):
        r = tranche.run(932, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TLS_SECURITY_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'tls_security_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(932, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(932, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
