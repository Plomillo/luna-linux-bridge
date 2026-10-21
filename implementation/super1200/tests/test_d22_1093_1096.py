#!/usr/bin/env python3
"""Negative tests for D22 1093-1096. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1093_1096 as tranche


class D22Tranche10931096Tests(unittest.TestCase):
    def test_cap_1093(self):
        r = tranche.run(1093, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_NETWORK_ESCAPE_TEST')
        self.assertEqual(r["kind"], 'SECURITY_TEST')
        self.assertEqual(r["binding"], 'quarantine_network_escape_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1093, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1093, {"canonical_name": "OTHER"})
    def test_cap_1094(self):
        r = tranche.run(1094, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_PRIVILEGE_TEST')
        self.assertEqual(r["kind"], 'SECURITY_TEST')
        self.assertEqual(r["binding"], 'quarantine_privilege_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1094, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1094, {"canonical_name": "OTHER"})
    def test_cap_1095(self):
        r = tranche.run(1095, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_PERSISTENCE_TEST')
        self.assertEqual(r["kind"], 'SECURITY_TEST')
        self.assertEqual(r["binding"], 'quarantine_persistence_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1095, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1095, {"canonical_name": "OTHER"})
    def test_cap_1096(self):
        r = tranche.run(1096, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_HOST_CONTAMINATION_TEST')
        self.assertEqual(r["kind"], 'SECURITY_TEST')
        self.assertEqual(r["binding"], 'quarantine_host_contamination_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1096, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1096, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
