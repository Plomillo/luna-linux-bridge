#!/usr/bin/env python3
"""Negative tests for D10 438-441. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d10_438_441 as tranche


class D10Tranche438441Tests(unittest.TestCase):
    def test_cap_0438(self):
        r = tranche.run(438, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LANGUAGE_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'language_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(438, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(438, {"canonical_name": "OTHER"})
    def test_cap_0439(self):
        r = tranche.run(439, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GRAMMAR_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'grammar_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(439, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(439, {"canonical_name": "OTHER"})
    def test_cap_0440(self):
        r = tranche.run(440, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LEXER_GENERATOR')
        self.assertEqual(r["kind"], 'LANGUAGE_TOOL')
        self.assertEqual(r["binding"], 'lexer_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(440, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(440, {"canonical_name": "OTHER"})
    def test_cap_0441(self):
        r = tranche.run(441, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PARSER_GENERATOR')
        self.assertEqual(r["kind"], 'LANGUAGE_TOOL')
        self.assertEqual(r["binding"], 'parser_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(441, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(441, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
