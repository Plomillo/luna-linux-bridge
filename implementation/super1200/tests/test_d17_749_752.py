#!/usr/bin/env python3
"""Negative tests for D17 749-752. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d17_749_752 as tranche


class D17Tranche749752Tests(unittest.TestCase):
    def test_cap_0749(self):
        r = tranche.run(749, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INTEREST_GRAPH')
        self.assertEqual(r["kind"], 'KNOWLEDGE_GRAPH')
        self.assertEqual(r["binding"], 'interest_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(749, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(749, {"canonical_name": "OTHER"})
    def test_cap_0750(self):
        r = tranche.run(750, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INTEREST_TO_COMPETENCY_ENGINE')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'interest_to_competency_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(750, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(750, {"canonical_name": "OTHER"})
    def test_cap_0751(self):
        r = tranche.run(751, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPETENCY_AMPLIFIER')
        self.assertEqual(r["kind"], 'ORCHESTRATION_ENGINE')
        self.assertEqual(r["binding"], 'competency_amplifier')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(751, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(751, {"canonical_name": "OTHER"})
    def test_cap_0752(self):
        r = tranche.run(752, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROJECT_INCUBATOR')
        self.assertEqual(r["kind"], 'WORKFLOW_ENGINE')
        self.assertEqual(r["binding"], 'project_incubator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(752, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(752, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
