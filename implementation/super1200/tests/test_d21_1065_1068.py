#!/usr/bin/env python3
"""Negative tests for D21 1065-1068. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1065_1068 as tranche


class D21Tranche10651068Tests(unittest.TestCase):
    def test_cap_1065(self):
        r = tranche.run(1065, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_SECURITY_TEST')
        self.assertEqual(r["kind"], 'SECURITY_TEST')
        self.assertEqual(r["binding"], 'substitute_security_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1065, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1065, {"canonical_name": "OTHER"})
    def test_cap_1066(self):
        r = tranche.run(1066, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_ADVERSARIAL_TEST')
        self.assertEqual(r["kind"], 'DEFENSIVE_TEST')
        self.assertEqual(r["binding"], 'substitute_adversarial_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1066, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1066, {"canonical_name": "OTHER"})
    def test_cap_1067(self):
        r = tranche.run(1067, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_DIFFERENTIAL_TEST')
        self.assertEqual(r["kind"], 'TEST_ENGINE')
        self.assertEqual(r["binding"], 'substitute_differential_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1067, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1067, {"canonical_name": "OTHER"})
    def test_cap_1068(self):
        r = tranche.run(1068, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_NON_REGRESSION')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'substitute_non_regression')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1068, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1068, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
