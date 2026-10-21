#!/usr/bin/env python3
"""Negative tests for D18 825-828. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_825_828 as tranche


class D18Tranche825828Tests(unittest.TestCase):
    def test_cap_0825(self):
        r = tranche.run(825, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PATCH_MINIMALITY_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'patch_minimality_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(825, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(825, {"canonical_name": "OTHER"})
    def test_cap_0826(self):
        r = tranche.run(826, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PATCH_DEPENDENCY_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'patch_dependency_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(826, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(826, {"canonical_name": "OTHER"})
    def test_cap_0827(self):
        r = tranche.run(827, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PATCH_BACKPORT_ENGINE')
        self.assertEqual(r["kind"], 'PATCH_ENGINE')
        self.assertEqual(r["binding"], 'patch_backport_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(827, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(827, {"canonical_name": "OTHER"})
    def test_cap_0828(self):
        r = tranche.run(828, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PATCH_FORWARD_PORT_ENGINE')
        self.assertEqual(r["kind"], 'PATCH_ENGINE')
        self.assertEqual(r["binding"], 'patch_forward_port_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(828, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(828, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
