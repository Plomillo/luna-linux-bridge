#!/usr/bin/env python3
"""Negative tests for D18 781-784. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_781_784 as tranche


class D18Tranche781784Tests(unittest.TestCase):
    def test_cap_0781(self):
        r = tranche.run(781, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CHANGE_RADIUS_ENGINE')
        self.assertEqual(r["kind"], 'IMPACT_ENGINE')
        self.assertEqual(r["binding"], 'change_radius_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(781, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(781, {"canonical_name": "OTHER"})
    def test_cap_0782(self):
        r = tranche.run(782, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MINIMAL_CHANGE_PLANNER')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'minimal_change_planner')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(782, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(782, {"canonical_name": "OTHER"})
    def test_cap_0783(self):
        r = tranche.run(783, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CHANGE_ISOLATION_ENGINE')
        self.assertEqual(r["kind"], 'CONTROL_ENGINE')
        self.assertEqual(r["binding"], 'change_isolation_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(783, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(783, {"canonical_name": "OTHER"})
    def test_cap_0784(self):
        r = tranche.run(784, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CHANGE_DEPENDENCY_CLOSURE')
        self.assertEqual(r["kind"], 'GRAPH_ENGINE')
        self.assertEqual(r["binding"], 'change_dependency_closure')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(784, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(784, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
