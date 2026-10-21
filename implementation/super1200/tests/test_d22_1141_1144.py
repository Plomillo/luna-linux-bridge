#!/usr/bin/env python3
"""Negative tests for D22 1141-1144. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1141_1144 as tranche


class D22Tranche11411144Tests(unittest.TestCase):
    def test_cap_1141(self):
        r = tranche.run(1141, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPLOITED_VULNERABILITY_LINKER')
        self.assertEqual(r["kind"], 'GRAPH_ENGINE')
        self.assertEqual(r["binding"], 'exploited_vulnerability_linker')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1141, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1141, {"canonical_name": "OTHER"})
    def test_cap_1142(self):
        r = tranche.run(1142, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PLATFORM_TARGET_GRAPH')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'platform_target_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1142, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1142, {"canonical_name": "OTHER"})
    def test_cap_1143(self):
        r = tranche.run(1143, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_TECHNOLOGY_EVOLUTION')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'malware_technology_evolution')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1143, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1143, {"canonical_name": "OTHER"})
    def test_cap_1144(self):
        r = tranche.run(1144, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_SIMILARITY_ENGINE')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'threat_similarity_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1144, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1144, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
