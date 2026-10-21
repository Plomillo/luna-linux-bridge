#!/usr/bin/env python3
"""Negative tests for D22 1169-1172. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1169_1172 as tranche


class D22Tranche11691172Tests(unittest.TestCase):
    def test_cap_1169(self):
        r = tranche.run(1169, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ECONOMICS_OF_CYBERCRIME')
        self.assertEqual(r["kind"], 'INTERDISCIPLINARY_DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'economics_of_cybercrime')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1169, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1169, {"canonical_name": "OTHER"})
    def test_cap_1170(self):
        r = tranche.run(1170, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HISTORY_OF_CYBERCRIME')
        self.assertEqual(r["kind"], 'HISTORICAL_DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'history_of_cybercrime')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1170, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1170, {"canonical_name": "OTHER"})
    def test_cap_1171(self):
        r = tranche.run(1171, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_ACTOR_MOTIVATION_TAXONOMY')
        self.assertEqual(r["kind"], 'DEFENSIVE_ONTOLOGY')
        self.assertEqual(r["binding"], 'threat_actor_motivation_taxonomy')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1171, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1171, {"canonical_name": "OTHER"})
    def test_cap_1172(self):
        r = tranche.run(1172, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_OBJECTIVE_ENGINE')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'threat_objective_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1172, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1172, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
