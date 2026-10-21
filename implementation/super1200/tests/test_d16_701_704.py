#!/usr/bin/env python3
"""Negative tests for D16 701-704. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d16_701_704 as tranche


class D16Tranche701704Tests(unittest.TestCase):
    def test_cap_0701(self):
        r = tranche.run(701, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'WINDOWS_COMPATIBILITY_FABRIC')
        self.assertEqual(r["kind"], 'COMPATIBILITY_FABRIC')
        self.assertEqual(r["binding"], 'windows_compatibility_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(701, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(701, {"canonical_name": "OTHER"})
    def test_cap_0702(self):
        r = tranche.run(702, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'WINE_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_COMPATIBILITY_RUNTIME')
        self.assertEqual(r["binding"], 'wine_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(702, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(702, {"canonical_name": "OTHER"})
    def test_cap_0703(self):
        r = tranche.run(703, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROTON_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_COMPATIBILITY_RUNTIME')
        self.assertEqual(r["binding"], 'proton_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(703, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(703, {"canonical_name": "OTHER"})
    def test_cap_0704(self):
        r = tranche.run(704, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'WIN32_API_COMPATIBILITY_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'win32_api_compatibility_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(704, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(704, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
