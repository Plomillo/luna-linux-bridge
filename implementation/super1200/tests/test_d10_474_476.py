#!/usr/bin/env python3
"""Negative tests for D10 474-476. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d10_474_476 as tranche


class D10Tranche474476Tests(unittest.TestCase):
    def test_cap_0474(self):
        r = tranche.run(474, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_COMPATIBILITY_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'engine_compatibility_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(474, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(474, {"canonical_name": "OTHER"})
    def test_cap_0475(self):
        r = tranche.run(475, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_ROLLBACK_TEMPLATE')
        self.assertEqual(r["kind"], 'TEMPLATE')
        self.assertEqual(r["binding"], 'engine_rollback_template')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(475, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(475, {"canonical_name": "OTHER"})
    def test_cap_0476(self):
        r = tranche.run(476, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_DOCUMENTATION_GENERATOR')
        self.assertEqual(r["kind"], 'FACTORY_TOOL')
        self.assertEqual(r["binding"], 'engine_documentation_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(476, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(476, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
