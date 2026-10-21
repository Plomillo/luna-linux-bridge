#!/usr/bin/env python3
"""Negative tests for D21 1017-1020. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1017_1020 as tranche


class D21Tranche10171020Tests(unittest.TestCase):
    def test_cap_1017(self):
        r = tranche.run(1017, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HTML_SANITIZATION_ENGINE')
        self.assertEqual(r["kind"], 'FORMAT_ENGINE')
        self.assertEqual(r["binding"], 'html_sanitization_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1017, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1017, {"canonical_name": "OTHER"})
    def test_cap_1018(self):
        r = tranche.run(1018, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SCRIPT_SANITIZATION_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'script_sanitization_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1018, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1018, {"canonical_name": "OTHER"})
    def test_cap_1019(self):
        r = tranche.run(1019, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOURCE_CODE_RECOVERY_ENGINE')
        self.assertEqual(r["kind"], 'RECOVERY_ENGINE')
        self.assertEqual(r["binding"], 'source_code_recovery_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1019, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1019, {"canonical_name": "OTHER"})
    def test_cap_1020(self):
        r = tranche.run(1020, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BINARY_SANITIZATION_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'binary_sanitization_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1020, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1020, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
