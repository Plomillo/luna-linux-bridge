#!/usr/bin/env python3
"""Negative tests for D18 813-816. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_813_816 as tranche


class D18Tranche813816Tests(unittest.TestCase):
    def test_cap_0813(self):
        r = tranche.run(813, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SCHEMA_EVOLUTION_ENGINE')
        self.assertEqual(r["kind"], 'SCHEMA_ENGINE')
        self.assertEqual(r["binding"], 'schema_evolution_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(813, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(813, {"canonical_name": "OTHER"})
    def test_cap_0814(self):
        r = tranche.run(814, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DATA_MIGRATION_ENGINE')
        self.assertEqual(r["kind"], 'MIGRATION_ENGINE')
        self.assertEqual(r["binding"], 'data_migration_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(814, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(814, {"canonical_name": "OTHER"})
    def test_cap_0815(self):
        r = tranche.run(815, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MIGRATION_PREFLIGHT')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'migration_preflight')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(815, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(815, {"canonical_name": "OTHER"})
    def test_cap_0816(self):
        r = tranche.run(816, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MIGRATION_DRY_RUN')
        self.assertEqual(r["kind"], 'SIMULATION_ENGINE')
        self.assertEqual(r["binding"], 'migration_dry_run')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(816, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(816, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
