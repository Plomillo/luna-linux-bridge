#!/usr/bin/env python3
"""Negative tests for D19 873-876. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_873_876 as tranche


class D19Tranche873876Tests(unittest.TestCase):
    def test_cap_0873(self):
        r = tranche.run(873, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_HYPOTHESIS_ENGINE')
        self.assertEqual(r["kind"], 'EPISTEMIC_ENGINE')
        self.assertEqual(r["binding"], 'security_hypothesis_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(873, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(873, {"canonical_name": "OTHER"})
    def test_cap_0874(self):
        r = tranche.run(874, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_CONSENSUS_ENGINE')
        self.assertEqual(r["kind"], 'CONSENSUS_ENGINE')
        self.assertEqual(r["binding"], 'security_consensus_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(874, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(874, {"canonical_name": "OTHER"})
    def test_cap_0875(self):
        r = tranche.run(875, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_DISAGREEMENT_ENGINE')
        self.assertEqual(r["kind"], 'CONFLICT_ENGINE')
        self.assertEqual(r["binding"], 'security_disagreement_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(875, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(875, {"canonical_name": "OTHER"})
    def test_cap_0876(self):
        r = tranche.run(876, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FALSE_POSITIVE_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'false_positive_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(876, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(876, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
