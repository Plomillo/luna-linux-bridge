#!/usr/bin/env python3
"""Negative tests for D22 1185-1188. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1185_1188 as tranche


class D22Tranche11851188Tests(unittest.TestCase):
    def test_cap_1185(self):
        r = tranche.run(1185, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ATTRIBUTION_UNCERTAINTY_GATE')
        self.assertEqual(r["kind"], 'EPISTEMIC_SECURITY_GATE')
        self.assertEqual(r["binding"], 'attribution_uncertainty_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1185, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1185, {"canonical_name": "OTHER"})
    def test_cap_1186(self):
        r = tranche.run(1186, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HUMAN_INTENT_TECHNICAL_MAPPING')
        self.assertEqual(r["kind"], 'DEFENSIVE_SEMANTIC_ADAPTER')
        self.assertEqual(r["binding"], 'human_intent_technical_mapping')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1186, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1186, {"canonical_name": "OTHER"})
    def test_cap_1187(self):
        r = tranche.run(1187, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PRE_ATTACK_INDICATOR_ENGINE')
        self.assertEqual(r["kind"], 'DEFENSIVE_DETECTION_ENGINE')
        self.assertEqual(r["binding"], 'pre_attack_indicator_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1187, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1187, {"canonical_name": "OTHER"})
    def test_cap_1188(self):
        r = tranche.run(1188, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREVENTION_HYPOTHESIS_ENGINE')
        self.assertEqual(r["kind"], 'DEFENSIVE_REASONING_ENGINE')
        self.assertEqual(r["binding"], 'prevention_hypothesis_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1188, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1188, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
