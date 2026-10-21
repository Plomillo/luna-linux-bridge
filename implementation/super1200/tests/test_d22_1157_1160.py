#!/usr/bin/env python3
"""Negative tests for D22 1157-1160. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1157_1160 as tranche


class D22Tranche11571160Tests(unittest.TestCase):
    def test_cap_1157(self):
        r = tranche.run(1157, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_INTELLIGENCE_CONFLICT_RESOLUTION')
        self.assertEqual(r["kind"], 'CONFLICT_ENGINE')
        self.assertEqual(r["binding"], 'threat_intelligence_conflict_resolution')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1157, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1157, {"canonical_name": "OTHER"})
    def test_cap_1158(self):
        r = tranche.run(1158, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_KNOWLEDGE_STALENESS_ENGINE')
        self.assertEqual(r["kind"], 'VALIDITY_ENGINE')
        self.assertEqual(r["binding"], 'threat_knowledge_staleness_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1158, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1158, {"canonical_name": "OTHER"})
    def test_cap_1159(self):
        r = tranche.run(1159, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OFFLINE_THREAT_REASONING_ENGINE')
        self.assertEqual(r["kind"], 'DEFENSIVE_REASONING_ENGINE')
        self.assertEqual(r["binding"], 'offline_threat_reasoning_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1159, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1159, {"canonical_name": "OTHER"})
    def test_cap_1160(self):
        r = tranche.run(1160, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREDICTIVE_DEFENSE_ENGINE')
        self.assertEqual(r["kind"], 'PREDICTIVE_DEFENSIVE_ENGINE')
        self.assertEqual(r["binding"], 'predictive_defense_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1160, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1160, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
