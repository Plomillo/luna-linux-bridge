#!/usr/bin/env python3
"""Negative tests for D13 586-589. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_586_589 as tranche


class D13Tranche586589Tests(unittest.TestCase):
    def test_cap_0586(self):
        r = tranche.run(586, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PEDAGOGICAL_FABRIC')
        self.assertEqual(r["kind"], 'PEDAGOGY_FABRIC')
        self.assertEqual(r["binding"], 'pedagogical_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(586, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(586, {"canonical_name": "OTHER"})
    def test_cap_0587(self):
        r = tranche.run(587, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LEARNING_OBJECT_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'learning_object_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(587, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(587, {"canonical_name": "OTHER"})
    def test_cap_0588(self):
        r = tranche.run(588, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREREQUISITE_GRAPH')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'prerequisite_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(588, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(588, {"canonical_name": "OTHER"})
    def test_cap_0589(self):
        r = tranche.run(589, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'KNOWLEDGE_GRAPH_PEDAGOGICAL_VIEW')
        self.assertEqual(r["kind"], 'GRAPH_VIEW')
        self.assertEqual(r["binding"], 'knowledge_graph_pedagogical_view')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(589, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(589, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
