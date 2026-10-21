#!/usr/bin/env python3
"""Negative tests for D21 1073-1076. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1073_1076 as tranche


class D21Tranche10731076Tests(unittest.TestCase):
    def test_cap_1073(self):
        r = tranche.run(1073, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_INDEPENDENT_VALIDATION')
        self.assertEqual(r["kind"], 'G23_INTERFACE')
        self.assertEqual(r["binding"], 'substitute_independent_validation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1073, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1073, {"canonical_name": "OTHER"})
    def test_cap_1074(self):
        r = tranche.run(1074, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_CERTIFICATION')
        self.assertEqual(r["kind"], 'G24_INTERFACE')
        self.assertEqual(r["binding"], 'substitute_certification')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1074, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1074, {"canonical_name": "OTHER"})
    def test_cap_1075(self):
        r = tranche.run(1075, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_CANARY')
        self.assertEqual(r["kind"], 'DEPLOYMENT_ENGINE')
        self.assertEqual(r["binding"], 'substitute_canary')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1075, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1075, {"canonical_name": "OTHER"})
    def test_cap_1076(self):
        r = tranche.run(1076, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_PROMOTION_ENGINE')
        self.assertEqual(r["kind"], 'PROMOTION_ENGINE')
        self.assertEqual(r["binding"], 'substitute_promotion_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1076, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1076, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
