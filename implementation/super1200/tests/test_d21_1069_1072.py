#!/usr/bin/env python3
"""Negative tests for D21 1069-1072. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1069_1072 as tranche


class D21Tranche10691072Tests(unittest.TestCase):
    def test_cap_1069(self):
        r = tranche.run(1069, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_UNCERTAINTY_REPORT')
        self.assertEqual(r["kind"], 'REPORT_ARTIFACT')
        self.assertEqual(r["binding"], 'substitute_uncertainty_report')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1069, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1069, {"canonical_name": "OTHER"})
    def test_cap_1070(self):
        r = tranche.run(1070, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_CANDIDATE_IDENTITY')
        self.assertEqual(r["kind"], 'IDENTITY_PRIMITIVE')
        self.assertEqual(r["binding"], 'substitute_candidate_identity')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1070, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1070, {"canonical_name": "OTHER"})
    def test_cap_1071(self):
        r = tranche.run(1071, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_PRECOMMIT_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'substitute_precommit_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1071, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1071, {"canonical_name": "OTHER"})
    def test_cap_1072(self):
        r = tranche.run(1072, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_CHECKPOINT')
        self.assertEqual(r["kind"], 'CHECKPOINT')
        self.assertEqual(r["binding"], 'substitute_checkpoint')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1072, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1072, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
