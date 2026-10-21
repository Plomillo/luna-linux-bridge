#!/usr/bin/env python3
"""Negative tests for D09 433-436. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_433_436 as tranche


class D09Tranche433436Tests(unittest.TestCase):
    def test_cap_0433(self):
        r = tranche.run(433, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ROOT_ROTATION')
        self.assertEqual(r["kind"], 'TRUST_ENGINE')
        self.assertEqual(r["binding"], 'root_rotation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(433, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(433, {"canonical_name": "OTHER"})
    def test_cap_0434(self):
        r = tranche.run(434, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_CHANNELS')
        self.assertEqual(r["kind"], 'UPDATE_POLICY')
        self.assertEqual(r["binding"], 'update_channels')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(434, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(434, {"canonical_name": "OTHER"})
    def test_cap_0435(self):
        r = tranche.run(435, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CANARY_DEPLOYMENT')
        self.assertEqual(r["kind"], 'DEPLOYMENT_ENGINE')
        self.assertEqual(r["binding"], 'canary_deployment')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(435, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(435, {"canonical_name": "OTHER"})
    def test_cap_0436(self):
        r = tranche.run(436, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STAGED_ROLLOUT')
        self.assertEqual(r["kind"], 'DEPLOYMENT_ENGINE')
        self.assertEqual(r["binding"], 'staged_rollout')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(436, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(436, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
