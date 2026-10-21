#!/usr/bin/env python3
"""Negative tests for D19 917-920. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_917_920 as tranche


class D19Tranche917920Tests(unittest.TestCase):
    def test_cap_0917(self):
        r = tranche.run(917, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEPENDENCY_CONFUSION_DETECTOR')
        self.assertEqual(r["kind"], 'SUPPLY_CHAIN_DETECTOR')
        self.assertEqual(r["binding"], 'dependency_confusion_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(917, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(917, {"canonical_name": "OTHER"})
    def test_cap_0918(self):
        r = tranche.run(918, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROVENANCE_SECURITY_GATE')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'provenance_security_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(918, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(918, {"canonical_name": "OTHER"})
    def test_cap_0919(self):
        r = tranche.run(919, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BUILD_INTEGRITY_SECURITY_GATE')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'build_integrity_security_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(919, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(919, {"canonical_name": "OTHER"})
    def test_cap_0920(self):
        r = tranche.run(920, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUPPLY_CHAIN_INCIDENT_GRAPH')
        self.assertEqual(r["kind"], 'INCIDENT_GRAPH')
        self.assertEqual(r["binding"], 'supply_chain_incident_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(920, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(920, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
