#!/usr/bin/env python3
"""Negative tests for D17 733-736. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d17_733_736 as tranche


class D17Tranche733736Tests(unittest.TestCase):
    def test_cap_0733(self):
        r = tranche.run(733, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPERT_DISAGREEMENT_ENGINE')
        self.assertEqual(r["kind"], 'CONFLICT_ENGINE')
        self.assertEqual(r["binding"], 'expert_disagreement_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(733, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(733, {"canonical_name": "OTHER"})
    def test_cap_0734(self):
        r = tranche.run(734, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREMORTEM_ENGINE')
        self.assertEqual(r["kind"], 'RISK_ENGINE')
        self.assertEqual(r["binding"], 'premortem_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(734, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(734, {"canonical_name": "OTHER"})
    def test_cap_0735(self):
        r = tranche.run(735, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'POSTMORTEM_ENGINE')
        self.assertEqual(r["kind"], 'INCIDENT_ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'postmortem_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(735, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(735, {"canonical_name": "OTHER"})
    def test_cap_0736(self):
        r = tranche.run(736, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RED_TEAM_ENGINE')
        self.assertEqual(r["kind"], 'ASSURANCE_ROLE_ENGINE')
        self.assertEqual(r["binding"], 'red_team_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(736, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(736, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
