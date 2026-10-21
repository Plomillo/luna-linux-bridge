#!/usr/bin/env python3
"""Negative tests for D13 598-601. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_598_601 as tranche


class D13Tranche598601Tests(unittest.TestCase):
    def test_cap_0598(self):
        r = tranche.run(598, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RETRIEVAL_PRACTICE_ENGINE')
        self.assertEqual(r["kind"], 'PEDAGOGY_ENGINE')
        self.assertEqual(r["binding"], 'retrieval_practice_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(598, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(598, {"canonical_name": "OTHER"})
    def test_cap_0599(self):
        r = tranche.run(599, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SPACED_REVIEW_ENGINE')
        self.assertEqual(r["kind"], 'SCHEDULER')
        self.assertEqual(r["binding"], 'spaced_review_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(599, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(599, {"canonical_name": "OTHER"})
    def test_cap_0600(self):
        r = tranche.run(600, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INTERLEAVED_PRACTICE_ENGINE')
        self.assertEqual(r["kind"], 'PEDAGOGY_ENGINE')
        self.assertEqual(r["binding"], 'interleaved_practice_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(600, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(600, {"canonical_name": "OTHER"})
    def test_cap_0601(self):
        r = tranche.run(601, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'WORKED_EXAMPLE_ENGINE')
        self.assertEqual(r["kind"], 'CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'worked_example_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(601, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(601, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
