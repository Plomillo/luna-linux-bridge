#!/usr/bin/env python3
"""Negative tests for D19 885-888. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_885_888 as tranche


class D19Tranche885888Tests(unittest.TestCase):
    def test_cap_0885(self):
        r = tranche.run(885, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BEHAVIORAL_MALWARE_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'behavioral_malware_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(885, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(885, {"canonical_name": "OTHER"})
    def test_cap_0886(self):
        r = tranche.run(886, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STATIC_MALWARE_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'static_malware_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(886, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(886, {"canonical_name": "OTHER"})
    def test_cap_0887(self):
        r = tranche.run(887, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DYNAMIC_MALWARE_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'dynamic_malware_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(887, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(887, {"canonical_name": "OTHER"})
    def test_cap_0888(self):
        r = tranche.run(888, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_SANDBOX')
        self.assertEqual(r["kind"], 'SANDBOX')
        self.assertEqual(r["binding"], 'malware_sandbox')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(888, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(888, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
