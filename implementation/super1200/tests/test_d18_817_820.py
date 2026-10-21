#!/usr/bin/env python3
"""Negative tests for D18 817-820. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_817_820 as tranche


class D18Tranche817820Tests(unittest.TestCase):
    def test_cap_0817(self):
        r = tranche.run(817, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MIGRATION_REVERSIBILITY_ANALYZER')
        self.assertEqual(r["kind"], 'RISK_ENGINE')
        self.assertEqual(r["binding"], 'migration_reversibility_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(817, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(817, {"canonical_name": "OTHER"})
    def test_cap_0818(self):
        r = tranche.run(818, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MIGRATION_CHECKPOINT')
        self.assertEqual(r["kind"], 'CHECKPOINT_ENGINE')
        self.assertEqual(r["binding"], 'migration_checkpoint')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(818, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(818, {"canonical_name": "OTHER"})
    def test_cap_0819(self):
        r = tranche.run(819, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MIGRATION_POSTVALIDATION')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'migration_postvalidation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(819, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(819, {"canonical_name": "OTHER"})
    def test_cap_0820(self):
        r = tranche.run(820, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MIGRATION_RECEIPT')
        self.assertEqual(r["kind"], 'RECEIPT')
        self.assertEqual(r["binding"], 'migration_receipt')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(820, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(820, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
