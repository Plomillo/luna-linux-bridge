#!/usr/bin/env python3
"""Negative tests for D22 1145-1148. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1145_1148 as tranche


class D22Tranche11451148Tests(unittest.TestCase):
    def test_cap_1145(self):
        r = tranche.run(1145, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BEHAVIORAL_NEAREST_NEIGHBOR')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'behavioral_nearest_neighbor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1145, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1145, {"canonical_name": "OTHER"})
    def test_cap_1146(self):
        r = tranche.run(1146, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NOVELTY_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'novelty_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1146, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1146, {"canonical_name": "OTHER"})
    def test_cap_1147(self):
        r = tranche.run(1147, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HISTORICAL_PRIOR_ENGINE')
        self.assertEqual(r["kind"], 'EPISTEMIC_ENGINE')
        self.assertEqual(r["binding"], 'historical_prior_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1147, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1147, {"canonical_name": "OTHER"})
    def test_cap_1148(self):
        r = tranche.run(1148, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_PATTERN_GENERALIZER')
        self.assertEqual(r["kind"], 'KNOWLEDGE_ENGINE')
        self.assertEqual(r["binding"], 'threat_pattern_generalizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1148, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1148, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
