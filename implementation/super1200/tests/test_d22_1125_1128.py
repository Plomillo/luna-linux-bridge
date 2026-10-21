#!/usr/bin/env python3
"""Negative tests for D22 1125-1128. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1125_1128 as tranche


class D22Tranche11251128Tests(unittest.TestCase):
    def test_cap_1125(self):
        r = tranche.run(1125, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_VARIANT_GRAPH')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'malware_variant_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1125, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1125, {"canonical_name": "OTHER"})
    def test_cap_1126(self):
        r = tranche.run(1126, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_LINEAGE_ENGINE')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'malware_lineage_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1126, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1126, {"canonical_name": "OTHER"})
    def test_cap_1127(self):
        r = tranche.run(1127, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_TIMELINE_ENGINE')
        self.assertEqual(r["kind"], 'TIMELINE_ENGINE')
        self.assertEqual(r["binding"], 'malware_timeline_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1127, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1127, {"canonical_name": "OTHER"})
    def test_cap_1128(self):
        r = tranche.run(1128, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_BEHAVIOR_KB')
        self.assertEqual(r["kind"], 'KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'malware_behavior_kb')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1128, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1128, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
