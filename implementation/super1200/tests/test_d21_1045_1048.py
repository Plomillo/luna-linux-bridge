#!/usr/bin/env python3
"""Negative tests for D21 1045-1048. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1045_1048 as tranche


class D21Tranche10451048Tests(unittest.TestCase):
    def test_cap_1045(self):
        r = tranche.run(1045, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UTILITY_DEPENDENCY_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'utility_dependency_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1045, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1045, {"canonical_name": "OTHER"})
    def test_cap_1046(self):
        r = tranche.run(1046, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_BLOCKER_DETECTOR')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'quarantine_blocker_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1046, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1046, {"canonical_name": "OTHER"})
    def test_cap_1047(self):
        r = tranche.run(1047, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BLOCKED_CAPABILITY_ROUTER')
        self.assertEqual(r["kind"], 'ROUTING_ENGINE')
        self.assertEqual(r["binding"], 'blocked_capability_router')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1047, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1047, {"canonical_name": "OTHER"})
    def test_cap_1048(self):
        r = tranche.run(1048, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SAFE_PROVIDER_SEARCH')
        self.assertEqual(r["kind"], 'PROVIDER_DISCOVERY_ENGINE')
        self.assertEqual(r["binding"], 'safe_provider_search')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1048, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1048, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
