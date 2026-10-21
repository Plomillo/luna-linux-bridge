#!/usr/bin/env python3
"""Negative tests for D17 737-740. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d17_737_740 as tranche


class D17Tranche737740Tests(unittest.TestCase):
    def test_cap_0737(self):
        r = tranche.run(737, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BLUE_TEAM_ENGINE')
        self.assertEqual(r["kind"], 'ASSURANCE_ROLE_ENGINE')
        self.assertEqual(r["binding"], 'blue_team_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(737, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(737, {"canonical_name": "OTHER"})
    def test_cap_0738(self):
        r = tranche.run(738, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEVILS_ADVOCATE_ENGINE')
        self.assertEqual(r["kind"], 'REASONING_ENGINE')
        self.assertEqual(r["binding"], 'devils_advocate_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(738, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(738, {"canonical_name": "OTHER"})
    def test_cap_0739(self):
        r = tranche.run(739, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SENIOR_REVIEW_PROTOCOL')
        self.assertEqual(r["kind"], 'REVIEW_PROTOCOL')
        self.assertEqual(r["binding"], 'senior_review_protocol')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(739, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(739, {"canonical_name": "OTHER"})
    def test_cap_0740(self):
        r = tranche.run(740, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'WISDOM_CONSTRAINT_ENGINE')
        self.assertEqual(r["kind"], 'DECISION_GATE')
        self.assertEqual(r["binding"], 'wisdom_constraint_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(740, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(740, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
