#!/usr/bin/env python3
"""Negative tests for D22 1085-1088. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1085_1088 as tranche


class D22Tranche10851088Tests(unittest.TestCase):
    def test_cap_1085(self):
        r = tranche.run(1085, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MINIMUM_EVIDENCE_RETENTION')
        self.assertEqual(r["kind"], 'POLICY')
        self.assertEqual(r["binding"], 'minimum_evidence_retention')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1085, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1085, {"canonical_name": "OTHER"})
    def test_cap_1086(self):
        r = tranche.run(1086, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SAFE_EVIDENCE_DISTILLATION')
        self.assertEqual(r["kind"], 'FORENSIC_ENGINE')
        self.assertEqual(r["binding"], 'safe_evidence_distillation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1086, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1086, {"canonical_name": "OTHER"})
    def test_cap_1087(self):
        r = tranche.run(1087, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_KNOWLEDGE_EXTRACTION')
        self.assertEqual(r["kind"], 'KNOWLEDGE_ENGINE')
        self.assertEqual(r["binding"], 'malware_knowledge_extraction')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1087, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1087, {"canonical_name": "OTHER"})
    def test_cap_1088(self):
        r = tranche.run(1088, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_BEHAVIOR_SUMMARY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_ARTIFACT')
        self.assertEqual(r["binding"], 'threat_behavior_summary')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1088, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1088, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
