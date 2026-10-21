#!/usr/bin/env python3
"""Negative tests for D21 1001-1004. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1001_1004 as tranche


class D21Tranche10011004Tests(unittest.TestCase):
    def test_cap_1001(self):
        r = tranche.run(1001, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARTIFACT_SANITIZATION_FABRIC')
        self.assertEqual(r["kind"], 'SANITIZATION_FABRIC')
        self.assertEqual(r["binding"], 'artifact_sanitization_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1001, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1001, {"canonical_name": "OTHER"})
    def test_cap_1002(self):
        r = tranche.run(1002, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARTIFACT_COMPONENT_GRAPH')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'artifact_component_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1002, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1002, {"canonical_name": "OTHER"})
    def test_cap_1003(self):
        r = tranche.run(1003, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ACTIVE_CONTENT_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'active_content_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1003, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1003, {"canonical_name": "OTHER"})
    def test_cap_1004(self):
        r = tranche.run(1004, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALICIOUS_COMPONENT_LOCALIZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'malicious_component_localizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1004, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1004, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
