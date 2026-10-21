#!/usr/bin/env python3
"""Negative tests for D13 602-605. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_602_605 as tranche


class D13Tranche602605Tests(unittest.TestCase):
    def test_cap_0602(self):
        r = tranche.run(602, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FADING_GUIDANCE_ENGINE')
        self.assertEqual(r["kind"], 'PEDAGOGY_ENGINE')
        self.assertEqual(r["binding"], 'fading_guidance_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(602, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(602, {"canonical_name": "OTHER"})
    def test_cap_0603(self):
        r = tranche.run(603, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEEP_QUESTION_ENGINE')
        self.assertEqual(r["kind"], 'CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'deep_question_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(603, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(603, {"canonical_name": "OTHER"})
    def test_cap_0604(self):
        r = tranche.run(604, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MISCONCEPTION_REGISTRY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REGISTRY')
        self.assertEqual(r["binding"], 'misconception_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(604, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(604, {"canonical_name": "OTHER"})
    def test_cap_0605(self):
        r = tranche.run(605, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MISCONCEPTION_DETECTOR')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'misconception_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(605, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(605, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
