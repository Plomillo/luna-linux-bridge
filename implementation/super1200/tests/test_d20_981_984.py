#!/usr/bin/env python3
"""Negative tests for D20 981-984. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d20_981_984 as tranche


class D20Tranche981984Tests(unittest.TestCase):
    def test_cap_0981(self):
        r = tranche.run(981, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BEHAVIOR_GRAPH')
        self.assertEqual(r["kind"], 'FORENSIC_GRAPH')
        self.assertEqual(r["binding"], 'behavior_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(981, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(981, {"canonical_name": "OTHER"})
    def test_cap_0982(self):
        r = tranche.run(982, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'IOC_EXTRACTION_ENGINE')
        self.assertEqual(r["kind"], 'DEFENSIVE_ENGINE')
        self.assertEqual(r["binding"], 'ioc_extraction_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(982, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(982, {"canonical_name": "OTHER"})
    def test_cap_0983(self):
        r = tranche.run(983, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_CLASSIFICATION_GATE')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'malware_classification_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(983, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(983, {"canonical_name": "OTHER"})
    def test_cap_0984(self):
        r = tranche.run(984, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BENIGN_RELEASE_GATE')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'benign_release_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(984, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(984, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
