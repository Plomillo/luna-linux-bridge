#!/usr/bin/env python3
"""Negative tests for D21 1053-1056. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1053_1056 as tranche


class D21Tranche10531056Tests(unittest.TestCase):
    def test_cap_1053(self):
        r = tranche.run(1053, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SAFE_REIMPLEMENTATION_PLANNER')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'safe_reimplementation_planner')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1053, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1053, {"canonical_name": "OTHER"})
    def test_cap_1054(self):
        r = tranche.run(1054, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MINIMAL_SUBSTITUTE_ENGINE')
        self.assertEqual(r["kind"], 'IMPLEMENTATION_ENGINE')
        self.assertEqual(r["binding"], 'minimal_substitute_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1054, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1054, {"canonical_name": "OTHER"})
    def test_cap_1055(self):
        r = tranche.run(1055, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_PROVIDER_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'substitute_provider_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1055, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1055, {"canonical_name": "OTHER"})
    def test_cap_1056(self):
        r = tranche.run(1056, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_SANDBOX')
        self.assertEqual(r["kind"], 'SANDBOX')
        self.assertEqual(r["binding"], 'substitute_sandbox')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1056, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1056, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
