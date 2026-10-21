#!/usr/bin/env python3
"""Negative tests for D19 901-904. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_901_904 as tranche


class D19Tranche901904Tests(unittest.TestCase):
    def test_cap_0901(self):
        r = tranche.run(901, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'VULNERABILITY_MANAGEMENT_FABRIC')
        self.assertEqual(r["kind"], 'SECURITY_FABRIC')
        self.assertEqual(r["binding"], 'vulnerability_management_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(901, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(901, {"canonical_name": "OTHER"})
    def test_cap_0902(self):
        r = tranche.run(902, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OSV_PROVIDER')
        self.assertEqual(r["kind"], 'DATA_FEED_API_PROVIDER')
        self.assertEqual(r["binding"], 'osv_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(902, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(902, {"canonical_name": "OTHER"})
    def test_cap_0903(self):
        r = tranche.run(903, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NVD_ADAPTER')
        self.assertEqual(r["kind"], 'DATA_FEED_ADAPTER')
        self.assertEqual(r["binding"], 'nvd_adapter')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(903, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(903, {"canonical_name": "OTHER"})
    def test_cap_0904(self):
        r = tranche.run(904, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CVE_IDENTITY_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'cve_identity_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(904, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(904, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
