#!/usr/bin/env python3
"""Negative tests for D18 833-836. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_833_836 as tranche


class D18Tranche833836Tests(unittest.TestCase):
    def test_cap_0833(self):
        r = tranche.run(833, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_STAGED_ROLLOUT')
        self.assertEqual(r["kind"], 'DEPLOYMENT_ENGINE')
        self.assertEqual(r["binding"], 'update_staged_rollout')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(833, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(833, {"canonical_name": "OTHER"})
    def test_cap_0834(self):
        r = tranche.run(834, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_HEALTH_MONITOR')
        self.assertEqual(r["kind"], 'MONITOR')
        self.assertEqual(r["binding"], 'update_health_monitor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(834, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(834, {"canonical_name": "OTHER"})
    def test_cap_0835(self):
        r = tranche.run(835, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_ABORT_ENGINE')
        self.assertEqual(r["kind"], 'CONTROL_ENGINE')
        self.assertEqual(r["binding"], 'update_abort_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(835, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(835, {"canonical_name": "OTHER"})
    def test_cap_0836(self):
        r = tranche.run(836, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_AUTO_ROLLBACK')
        self.assertEqual(r["kind"], 'RECOVERY_ENGINE')
        self.assertEqual(r["binding"], 'update_auto_rollback')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(836, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(836, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
