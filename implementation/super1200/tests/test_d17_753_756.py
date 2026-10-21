#!/usr/bin/env python3
"""Negative tests for D17 753-756. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d17_753_756 as tranche


class D17Tranche753756Tests(unittest.TestCase):
    def test_cap_0753(self):
        r = tranche.run(753, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ECOSYSTEM_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'ecosystem_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(753, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(753, {"canonical_name": "OTHER"})
    def test_cap_0754(self):
        r = tranche.run(754, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COGNITIVE_UNIVERSE_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'cognitive_universe_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(754, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(754, {"canonical_name": "OTHER"})
    def test_cap_0755(self):
        r = tranche.run(755, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'METACOGNITIVE_UNIVERSE_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'metacognitive_universe_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(755, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(755, {"canonical_name": "OTHER"})
    def test_cap_0756(self):
        r = tranche.run(756, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ECOSYSTEM_INTEROPERABILITY_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'ecosystem_interoperability_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(756, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(756, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
