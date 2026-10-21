#!/usr/bin/env python3
"""Negative tests for D22 1121-1124. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1121_1124 as tranche


class D22Tranche11211124Tests(unittest.TestCase):
    def test_cap_1121(self):
        r = tranche.run(1121, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HISTORICAL_THREAT_INTELLIGENCE_FABRIC')
        self.assertEqual(r["kind"], 'DEFENSIVE_KNOWLEDGE_FABRIC')
        self.assertEqual(r["binding"], 'historical_threat_intelligence_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1121, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1121, {"canonical_name": "OTHER"})
    def test_cap_1122(self):
        r = tranche.run(1122, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_HISTORY_REGISTRY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REGISTRY')
        self.assertEqual(r["binding"], 'malware_history_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1122, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1122, {"canonical_name": "OTHER"})
    def test_cap_1123(self):
        r = tranche.run(1123, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_TAXONOMY_ENGINE')
        self.assertEqual(r["kind"], 'ONTOLOGY_ENGINE')
        self.assertEqual(r["binding"], 'malware_taxonomy_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1123, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1123, {"canonical_name": "OTHER"})
    def test_cap_1124(self):
        r = tranche.run(1124, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_FAMILY_REGISTRY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REGISTRY')
        self.assertEqual(r["binding"], 'malware_family_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1124, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1124, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
