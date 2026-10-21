#!/usr/bin/env python3
"""Negative tests for D21 1049-1052. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1049_1052 as tranche


class D21Tranche10491052Tests(unittest.TestCase):
    def test_cap_1049(self):
        r = tranche.run(1049, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TRUSTED_SOURCE_SUBSTITUTION')
        self.assertEqual(r["kind"], 'RECOVERY_PATTERN')
        self.assertEqual(r["binding"], 'trusted_source_substitution')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1049, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1049, {"canonical_name": "OTHER"})
    def test_cap_1050(self):
        r = tranche.run(1050, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FUNCTIONAL_EQUIVALENCE_ANALYZER')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'functional_equivalence_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1050, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1050, {"canonical_name": "OTHER"})
    def test_cap_1051(self):
        r = tranche.run(1051, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SAFE_SUBSTITUTE_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'safe_substitute_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1051, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1051, {"canonical_name": "OTHER"})
    def test_cap_1052(self):
        r = tranche.run(1052, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLEAN_ROOM_REQUIREMENTS')
        self.assertEqual(r["kind"], 'SECURITY_CONTRACT')
        self.assertEqual(r["binding"], 'clean_room_requirements')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1052, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1052, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
