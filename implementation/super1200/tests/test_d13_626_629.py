#!/usr/bin/env python3
"""Negative tests for D13 626-629. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_626_629 as tranche


class D13Tranche626629Tests(unittest.TestCase):
    def test_cap_0626(self):
        r = tranche.run(626, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ADAPTIVE_PATH_ENGINE')
        self.assertEqual(r["kind"], 'PEDAGOGY_ENGINE')
        self.assertEqual(r["binding"], 'adaptive_path_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(626, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(626, {"canonical_name": "OTHER"})
    def test_cap_0627(self):
        r = tranche.run(627, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DIFFICULTY_ESTIMATOR')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'difficulty_estimator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(627, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(627, {"canonical_name": "OTHER"})
    def test_cap_0628(self):
        r = tranche.run(628, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COGNITIVE_LOAD_MONITOR')
        self.assertEqual(r["kind"], 'PEDAGOGY_MONITOR')
        self.assertEqual(r["binding"], 'cognitive_load_monitor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(628, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(628, {"canonical_name": "OTHER"})
    def test_cap_0629(self):
        r = tranche.run(629, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CHUNKING_ENGINE')
        self.assertEqual(r["kind"], 'CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'chunking_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(629, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(629, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
