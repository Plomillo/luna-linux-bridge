#!/usr/bin/env python3
"""Negative tests for D22 1137-1140. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1137_1140 as tranche


class D22Tranche11371140Tests(unittest.TestCase):
    def test_cap_1137(self):
        r = tranche.run(1137, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEFENSE_EVASION_KB')
        self.assertEqual(r["kind"], 'KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'defense_evasion_kb')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1137, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1137, {"canonical_name": "OTHER"})
    def test_cap_1138(self):
        r = tranche.run(1138, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LATERAL_MOVEMENT_KB')
        self.assertEqual(r["kind"], 'KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'lateral_movement_kb')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1138, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1138, {"canonical_name": "OTHER"})
    def test_cap_1139(self):
        r = tranche.run(1139, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMMAND_CONTROL_INDICATOR_KB')
        self.assertEqual(r["kind"], 'KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'command_control_indicator_kb')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1139, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1139, {"canonical_name": "OTHER"})
    def test_cap_1140(self):
        r = tranche.run(1140, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'IMPACT_PATTERN_KB')
        self.assertEqual(r["kind"], 'KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'impact_pattern_kb')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1140, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1140, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
