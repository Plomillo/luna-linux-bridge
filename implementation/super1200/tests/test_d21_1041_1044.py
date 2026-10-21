#!/usr/bin/env python3
"""Negative tests for D21 1041-1044. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1041_1044 as tranche


class D21Tranche10411044Tests(unittest.TestCase):
    def test_cap_1041(self):
        r = tranche.run(1041, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_CONTINUITY_FABRIC')
        self.assertEqual(r["kind"], 'CONTINUITY_FABRIC')
        self.assertEqual(r["binding"], 'quarantine_continuity_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1041, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1041, {"canonical_name": "OTHER"})
    def test_cap_1042(self):
        r = tranche.run(1042, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINED_UTILITY_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'quarantined_utility_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1042, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1042, {"canonical_name": "OTHER"})
    def test_cap_1043(self):
        r = tranche.run(1043, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UTILITY_REQUIREMENT_EXTRACTOR')
        self.assertEqual(r["kind"], 'REQUIREMENTS_ENGINE')
        self.assertEqual(r["binding"], 'utility_requirement_extractor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1043, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1043, {"canonical_name": "OTHER"})
    def test_cap_1044(self):
        r = tranche.run(1044, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UTILITY_SEMANTIC_CONTRACT')
        self.assertEqual(r["kind"], 'CONTRACT')
        self.assertEqual(r["binding"], 'utility_semantic_contract')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1044, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1044, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
