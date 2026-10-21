#!/usr/bin/env python3
"""Negative tests for D13 614-617. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_614_617 as tranche


class D13Tranche614617Tests(unittest.TestCase):
    def test_cap_0614(self):
        r = tranche.run(614, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ABSTRACTION_LADDER_ENGINE')
        self.assertEqual(r["kind"], 'PEDAGOGY_ENGINE')
        self.assertEqual(r["binding"], 'abstraction_ladder_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(614, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(614, {"canonical_name": "OTHER"})
    def test_cap_0615(self):
        r = tranche.run(615, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MULTIMODAL_EXPLANATION_ENGINE')
        self.assertEqual(r["kind"], 'CONTENT_ORCHESTRATOR')
        self.assertEqual(r["binding"], 'multimodal_explanation_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(615, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(615, {"canonical_name": "OTHER"})
    def test_cap_0616(self):
        r = tranche.run(616, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANALOGY_ENGINE')
        self.assertEqual(r["kind"], 'CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'analogy_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(616, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(616, {"canonical_name": "OTHER"})
    def test_cap_0617(self):
        r = tranche.run(617, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXAMPLE_PROVENANCE_ENGINE')
        self.assertEqual(r["kind"], 'PROVENANCE_ENGINE')
        self.assertEqual(r["binding"], 'example_provenance_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(617, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(617, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
