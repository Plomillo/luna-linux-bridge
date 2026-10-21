#!/usr/bin/env python3
"""Negative tests for D13 606-609. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_606_609 as tranche


class D13Tranche606609Tests(unittest.TestCase):
    def test_cap_0606(self):
        r = tranche.run(606, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COUNTEREXAMPLE_GENERATOR')
        self.assertEqual(r["kind"], 'CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'counterexample_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(606, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(606, {"canonical_name": "OTHER"})
    def test_cap_0607(self):
        r = tranche.run(607, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOCRATIC_TUTOR_ENGINE')
        self.assertEqual(r["kind"], 'PEDAGOGY_ENGINE')
        self.assertEqual(r["binding"], 'socratic_tutor_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(607, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(607, {"canonical_name": "OTHER"})
    def test_cap_0608(self):
        r = tranche.run(608, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPLANATION_GENERATOR')
        self.assertEqual(r["kind"], 'CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'explanation_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(608, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(608, {"canonical_name": "OTHER"})
    def test_cap_0609(self):
        r = tranche.run(609, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REFERENCE_GENERATOR')
        self.assertEqual(r["kind"], 'CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'reference_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(609, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(609, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
