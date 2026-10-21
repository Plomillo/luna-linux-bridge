#!/usr/bin/env python3
"""Negative tests for D10 442-445. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d10_442_445 as tranche


class D10Tranche442445Tests(unittest.TestCase):
    def test_cap_0442(self):
        r = tranche.run(442, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AST_SCHEMA')
        self.assertEqual(r["kind"], 'SCHEMA')
        self.assertEqual(r["binding"], 'ast_schema')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(442, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(442, {"canonical_name": "OTHER"})
    def test_cap_0443(self):
        r = tranche.run(443, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SEMANTIC_ANALYZER')
        self.assertEqual(r["kind"], 'LANGUAGE_ENGINE')
        self.assertEqual(r["binding"], 'semantic_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(443, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(443, {"canonical_name": "OTHER"})
    def test_cap_0444(self):
        r = tranche.run(444, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TYPE_SYSTEM_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'type_system_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(444, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(444, {"canonical_name": "OTHER"})
    def test_cap_0445(self):
        r = tranche.run(445, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEPENDENT_TYPE_LANGUAGE_LAB')
        self.assertEqual(r["kind"], 'LAB')
        self.assertEqual(r["binding"], 'dependent_type_language_lab')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(445, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(445, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
