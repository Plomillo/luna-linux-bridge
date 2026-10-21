#!/usr/bin/env python3
"""Negative tests for D22 1173-1176. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1173_1176 as tranche


class D22Tranche11731176Tests(unittest.TestCase):
    def test_cap_1173(self):
        r = tranche.run(1173, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INCENTIVE_STRUCTURE_ANALYZER')
        self.assertEqual(r["kind"], 'INTERDISCIPLINARY_ANALYZER')
        self.assertEqual(r["binding"], 'incentive_structure_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1173, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1173, {"canonical_name": "OTHER"})
    def test_cap_1174(self):
        r = tranche.run(1174, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OPPORTUNITY_STRUCTURE_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_RISK_ANALYZER')
        self.assertEqual(r["binding"], 'opportunity_structure_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1174, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1174, {"canonical_name": "OTHER"})
    def test_cap_1175(self):
        r = tranche.run(1175, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TARGET_SELECTION_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'target_selection_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1175, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1175, {"canonical_name": "OTHER"})
    def test_cap_1176(self):
        r = tranche.run(1176, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOCIAL_ENGINEERING_KB')
        self.assertEqual(r["kind"], 'DEFENSIVE_KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'social_engineering_kb')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1176, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1176, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
