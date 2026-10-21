#!/usr/bin/env python3
"""Negative tests for D19 897-900. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_897_900 as tranche


class D19Tranche897900Tests(unittest.TestCase):
    def test_cap_0897(self):
        r = tranche.run(897, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PERSISTENCE_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'persistence_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(897, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(897, {"canonical_name": "OTHER"})
    def test_cap_0898(self):
        r = tranche.run(898, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALICIOUS_BEHAVIOR_GRAPH')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'malicious_behavior_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(898, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(898, {"canonical_name": "OTHER"})
    def test_cap_0899(self):
        r = tranche.run(899, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_FAMILY_CLASSIFIER')
        self.assertEqual(r["kind"], 'CLASSIFIER')
        self.assertEqual(r["binding"], 'malware_family_classifier')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(899, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(899, {"canonical_name": "OTHER"})
    def test_cap_0900(self):
        r = tranche.run(900, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_ANALYSIS_RECEIPT')
        self.assertEqual(r["kind"], 'RECEIPT')
        self.assertEqual(r["binding"], 'malware_analysis_receipt')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(900, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(900, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
