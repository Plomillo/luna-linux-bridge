#!/usr/bin/env python3
"""Negative tests for D09 397-400. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_397_400 as tranche


class D09Tranche397400Tests(unittest.TestCase):
    def test_cap_0397(self):
        r = tranche.run(397, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MOBILE_RESOURCE_BUDGET')
        self.assertEqual(r["kind"], 'RESOURCE_POLICY')
        self.assertEqual(r["binding"], 'mobile_resource_budget')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(397, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(397, {"canonical_name": "OTHER"})
    def test_cap_0398(self):
        r = tranche.run(398, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OFFLINE_MOBILE_RUNTIME')
        self.assertEqual(r["kind"], 'CONTINUITY_ENGINE')
        self.assertEqual(r["binding"], 'offline_mobile_runtime')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(398, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(398, {"canonical_name": "OTHER"})
    def test_cap_0399(self):
        r = tranche.run(399, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANDROID_UPDATE_ENGINE')
        self.assertEqual(r["kind"], 'UPDATE_ENGINE')
        self.assertEqual(r["binding"], 'android_update_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(399, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(399, {"canonical_name": "OTHER"})
    def test_cap_0400(self):
        r = tranche.run(400, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANDROID_RECOVERY_TEST')
        self.assertEqual(r["kind"], 'RECOVERY_TEST')
        self.assertEqual(r["binding"], 'android_recovery_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(400, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(400, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
