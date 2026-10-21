#!/usr/bin/env python3
"""Negative tests for D14 645-648. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d14_645_648 as tranche


class D14Tranche645648Tests(unittest.TestCase):
    def test_cap_0645(self):
        r = tranche.run(645, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_LEDGER')
        self.assertEqual(r["kind"], 'LEDGER')
        self.assertEqual(r["binding"], 'uncertainty_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(645, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(645, {"canonical_name": "OTHER"})
    def test_cap_0646(self):
        r = tranche.run(646, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_DEPENDENCY_GRAPH')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'uncertainty_dependency_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(646, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(646, {"canonical_name": "OTHER"})
    def test_cap_0647(self):
        r = tranche.run(647, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_PROPAGATION_ENGINE')
        self.assertEqual(r["kind"], 'EPISTEMIC_ENGINE')
        self.assertEqual(r["binding"], 'uncertainty_propagation_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(647, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(647, {"canonical_name": "OTHER"})
    def test_cap_0648(self):
        r = tranche.run(648, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUESTION_FROM_UNCERTAINTY_ENGINE')
        self.assertEqual(r["kind"], 'REASONING_ENGINE')
        self.assertEqual(r["binding"], 'question_from_uncertainty_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(648, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(648, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
