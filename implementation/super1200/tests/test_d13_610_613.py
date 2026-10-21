#!/usr/bin/env python3
"""Negative tests for D13 610-613. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_610_613 as tranche


class D13Tranche610613Tests(unittest.TestCase):
    def test_cap_0610(self):
        r = tranche.run(610, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HOW_TO_GENERATOR')
        self.assertEqual(r["kind"], 'CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'how_to_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(610, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(610, {"canonical_name": "OTHER"})
    def test_cap_0611(self):
        r = tranche.run(611, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TUTORIAL_GENERATOR')
        self.assertEqual(r["kind"], 'CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'tutorial_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(611, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(611, {"canonical_name": "OTHER"})
    def test_cap_0612(self):
        r = tranche.run(612, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DIATAXIS_CLASSIFIER')
        self.assertEqual(r["kind"], 'CLASSIFIER')
        self.assertEqual(r["binding"], 'diataxis_classifier')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(612, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(612, {"canonical_name": "OTHER"})
    def test_cap_0613(self):
        r = tranche.run(613, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPOSITORY_ARCHITECTURE_ENGINE')
        self.assertEqual(r["kind"], 'CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'expository_architecture_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(613, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(613, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
