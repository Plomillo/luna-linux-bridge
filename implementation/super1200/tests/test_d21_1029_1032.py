#!/usr/bin/env python3
"""Negative tests for D21 1029-1032. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1029_1032 as tranche


class D21Tranche10291032Tests(unittest.TestCase):
    def test_cap_1029(self):
        r = tranche.run(1029, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SANITIZATION_DIFF')
        self.assertEqual(r["kind"], 'DIFF_ENGINE')
        self.assertEqual(r["binding"], 'sanitization_diff')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1029, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1029, {"canonical_name": "OTHER"})
    def test_cap_1030(self):
        r = tranche.run(1030, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SANITIZATION_RECEIPT')
        self.assertEqual(r["kind"], 'RECEIPT')
        self.assertEqual(r["binding"], 'sanitization_receipt')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1030, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1030, {"canonical_name": "OTHER"})
    def test_cap_1031(self):
        r = tranche.run(1031, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SANITIZATION_ROLLBACK')
        self.assertEqual(r["kind"], 'RECOVERY_PATTERN')
        self.assertEqual(r["binding"], 'sanitization_rollback')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1031, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1031, {"canonical_name": "OTHER"})
    def test_cap_1032(self):
        r = tranche.run(1032, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SANITIZATION_SANDBOX_VALIDATION')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'sanitization_sandbox_validation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1032, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1032, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
