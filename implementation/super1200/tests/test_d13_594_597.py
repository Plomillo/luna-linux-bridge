#!/usr/bin/env python3
"""Negative tests for D13 594-597. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_594_597 as tranche


class D13Tranche594597Tests(unittest.TestCase):
    def test_cap_0594(self):
        r = tranche.run(594, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SKILL_GRAPH')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'skill_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(594, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(594, {"canonical_name": "OTHER"})
    def test_cap_0595(self):
        r = tranche.run(595, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MASTERY_CRITERIA_ENGINE')
        self.assertEqual(r["kind"], 'ASSESSMENT_POLICY')
        self.assertEqual(r["binding"], 'mastery_criteria_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(595, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(595, {"canonical_name": "OTHER"})
    def test_cap_0596(self):
        r = tranche.run(596, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FORMATIVE_ASSESSMENT_ENGINE')
        self.assertEqual(r["kind"], 'ASSESSMENT_ENGINE')
        self.assertEqual(r["binding"], 'formative_assessment_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(596, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(596, {"canonical_name": "OTHER"})
    def test_cap_0597(self):
        r = tranche.run(597, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUMMATIVE_ASSESSMENT_ENGINE')
        self.assertEqual(r["kind"], 'ASSESSMENT_ENGINE')
        self.assertEqual(r["binding"], 'summative_assessment_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(597, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(597, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
