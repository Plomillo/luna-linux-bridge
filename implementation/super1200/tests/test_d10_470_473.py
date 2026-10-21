#!/usr/bin/env python3
"""Negative tests for D10 470-473. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d10_470_473 as tranche


class D10Tranche470473Tests(unittest.TestCase):
    def test_cap_0470(self):
        r = tranche.run(470, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_SECURITY_TEMPLATE')
        self.assertEqual(r["kind"], 'TEMPLATE')
        self.assertEqual(r["binding"], 'engine_security_template')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(470, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(470, {"canonical_name": "OTHER"})
    def test_cap_0471(self):
        r = tranche.run(471, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_CERTIFICATION_TEMPLATE')
        self.assertEqual(r["kind"], 'TEMPLATE')
        self.assertEqual(r["binding"], 'engine_certification_template')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(471, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(471, {"canonical_name": "OTHER"})
    def test_cap_0472(self):
        r = tranche.run(472, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_DEPENDENCY_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'engine_dependency_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(472, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(472, {"canonical_name": "OTHER"})
    def test_cap_0473(self):
        r = tranche.run(473, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_NON_DUPLICATION_GATE')
        self.assertEqual(r["kind"], 'G16_GATE')
        self.assertEqual(r["binding"], 'engine_non_duplication_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(473, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(473, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
