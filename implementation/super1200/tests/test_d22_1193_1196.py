#!/usr/bin/env python3
"""Negative tests for D22 1193-1196. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1193_1196 as tranche


class D22Tranche11931196Tests(unittest.TestCase):
    def test_cap_1193(self):
        r = tranche.run(1193, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_EARLY_WARNING_ENGINE')
        self.assertEqual(r["kind"], 'DEFENSIVE_WARNING_ENGINE')
        self.assertEqual(r["binding"], 'threat_early_warning_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1193, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1193, {"canonical_name": "OTHER"})
    def test_cap_1194(self):
        r = tranche.run(1194, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREVENT_BEFORE_DOWNLOAD_ENGINE')
        self.assertEqual(r["kind"], 'PRE_EXECUTION_SECURITY_GATE')
        self.assertEqual(r["binding"], 'prevent_before_download_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1194, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1194, {"canonical_name": "OTHER"})
    def test_cap_1195(self):
        r = tranche.run(1195, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREVENT_BEFORE_EXECUTION_ENGINE')
        self.assertEqual(r["kind"], 'PRE_EXECUTION_SECURITY_GATE')
        self.assertEqual(r["binding"], 'prevent_before_execution_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1195, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1195, {"canonical_name": "OTHER"})
    def test_cap_1196(self):
        r = tranche.run(1196, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREVENT_BEFORE_PRIVILEGE_ENGINE')
        self.assertEqual(r["kind"], 'PRIVILEGE_SECURITY_GATE')
        self.assertEqual(r["binding"], 'prevent_before_privilege_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1196, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1196, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
