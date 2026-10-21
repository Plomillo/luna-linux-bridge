#!/usr/bin/env python3
"""Negative tests for D22 1097-1100. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1097_1100 as tranche


class D22Tranche10971100Tests(unittest.TestCase):
    def test_cap_1097(self):
        r = tranche.run(1097, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SANDBOX_INTEGRITY_MONITOR')
        self.assertEqual(r["kind"], 'MONITOR')
        self.assertEqual(r["binding"], 'sandbox_integrity_monitor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1097, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1097, {"canonical_name": "OTHER"})
    def test_cap_1098(self):
        r = tranche.run(1098, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANALYZER_COMPROMISE_MONITOR')
        self.assertEqual(r["kind"], 'MONITOR')
        self.assertEqual(r["binding"], 'analyzer_compromise_monitor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1098, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1098, {"canonical_name": "OTHER"})
    def test_cap_1099(self):
        r = tranche.run(1099, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_TOOL_ISOLATION')
        self.assertEqual(r["kind"], 'SECURITY_BOUNDARY')
        self.assertEqual(r["binding"], 'security_tool_isolation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1099, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1099, {"canonical_name": "OTHER"})
    def test_cap_1100(self):
        r = tranche.run(1100, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DISPOSABLE_ANALYSIS_ENVIRONMENT')
        self.assertEqual(r["kind"], 'SANDBOX_PATTERN')
        self.assertEqual(r["binding"], 'disposable_analysis_environment')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1100, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1100, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
