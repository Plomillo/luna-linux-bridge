#!/usr/bin/env python3
"""Negative tests for D17 745-748. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d17_745_748 as tranche


class D17Tranche745748Tests(unittest.TestCase):
    def test_cap_0745(self):
        r = tranche.run(745, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DECADE_MIGRATION_TEST')
        self.assertEqual(r["kind"], 'RESILIENCE_TEST')
        self.assertEqual(r["binding"], 'decade_migration_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(745, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(745, {"canonical_name": "OTHER"})
    def test_cap_0746(self):
        r = tranche.run(746, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARCHAEOLOGICAL_RECONSTRUCTION_ENGINE')
        self.assertEqual(r["kind"], 'FORENSIC_ENGINE')
        self.assertEqual(r["binding"], 'archaeological_reconstruction_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(746, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(746, {"canonical_name": "OTHER"})
    def test_cap_0747(self):
        r = tranche.run(747, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PERSONAL_WORK_PATTERN_MODEL')
        self.assertEqual(r["kind"], 'USER_WORKFLOW_MODEL')
        self.assertEqual(r["binding"], 'personal_work_pattern_model')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(747, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(747, {"canonical_name": "OTHER"})
    def test_cap_0748(self):
        r = tranche.run(748, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ATTENTION_ORGANIZATION_ENGINE')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'attention_organization_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(748, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(748, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
