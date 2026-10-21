#!/usr/bin/env python3
"""Negative tests for D16 709-712. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d16_709_712 as tranche


class D16Tranche709712Tests(unittest.TestCase):
    def test_cap_0709(self):
        r = tranche.run(709, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GAME_COMPATIBILITY_KB')
        self.assertEqual(r["kind"], 'KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'game_compatibility_kb')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(709, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(709, {"canonical_name": "OTHER"})
    def test_cap_0710(self):
        r = tranche.run(710, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GAME_PROFILE_ENGINE')
        self.assertEqual(r["kind"], 'PROFILE_ENGINE')
        self.assertEqual(r["binding"], 'game_profile_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(710, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(710, {"canonical_name": "OTHER"})
    def test_cap_0711(self):
        r = tranche.run(711, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FRAME_TIME_ANALYZER')
        self.assertEqual(r["kind"], 'PERFORMANCE_ANALYZER')
        self.assertEqual(r["binding"], 'frame_time_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(711, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(711, {"canonical_name": "OTHER"})
    def test_cap_0712(self):
        r = tranche.run(712, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SHADER_STUTTER_ANALYZER')
        self.assertEqual(r["kind"], 'PERFORMANCE_ANALYZER')
        self.assertEqual(r["binding"], 'shader_stutter_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(712, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(712, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
