#!/usr/bin/env python3
"""Negative tests for D22 1177-1180. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1177_1180 as tranche


class D22Tranche11771180Tests(unittest.TestCase):
    def test_cap_1177(self):
        r = tranche.run(1177, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DECEPTION_PATTERN_REGISTRY')
        self.assertEqual(r["kind"], 'DEFENSIVE_REGISTRY')
        self.assertEqual(r["binding"], 'deception_pattern_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1177, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1177, {"canonical_name": "OTHER"})
    def test_cap_1178(self):
        r = tranche.run(1178, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TRUST_ABUSE_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'trust_abuse_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1178, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1178, {"canonical_name": "OTHER"})
    def test_cap_1179(self):
        r = tranche.run(1179, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HUMAN_VULNERABILITY_MODEL')
        self.assertEqual(r["kind"], 'DEFENSIVE_HUMAN_FACTORS_MODEL')
        self.assertEqual(r["binding"], 'human_vulnerability_model')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1179, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1179, {"canonical_name": "OTHER"})
    def test_cap_1180(self):
        r = tranche.run(1180, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_DECISION_BIAS_ANALYZER')
        self.assertEqual(r["kind"], 'METACOGNITIVE_SECURITY_ENGINE')
        self.assertEqual(r["binding"], 'security_decision_bias_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1180, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1180, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
