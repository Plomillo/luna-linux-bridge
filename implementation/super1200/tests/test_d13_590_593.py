#!/usr/bin/env python3
"""Negative tests for D13 590-593. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_590_593 as tranche


class D13Tranche590593Tests(unittest.TestCase):
    def test_cap_0590(self):
        r = tranche.run(590, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LEARNER_MODEL')
        self.assertEqual(r["kind"], 'STATE_MODEL')
        self.assertEqual(r["binding"], 'learner_model')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(590, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(590, {"canonical_name": "OTHER"})
    def test_cap_0591(self):
        r = tranche.run(591, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'KNOWLEDGE_STATE_ESTIMATOR')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'knowledge_state_estimator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(591, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(591, {"canonical_name": "OTHER"})
    def test_cap_0592(self):
        r = tranche.run(592, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LEARNING_OBJECTIVE_ENGINE')
        self.assertEqual(r["kind"], 'PEDAGOGY_ENGINE')
        self.assertEqual(r["binding"], 'learning_objective_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(592, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(592, {"canonical_name": "OTHER"})
    def test_cap_0593(self):
        r = tranche.run(593, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPETENCY_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'competency_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(593, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(593, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
