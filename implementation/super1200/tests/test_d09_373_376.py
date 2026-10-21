#!/usr/bin/env python3
"""Negative tests for D09 373-376. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_373_376 as tranche


class D09Tranche373376Tests(unittest.TestCase):
    def test_cap_0373(self):
        r = tranche.run(373, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RSYNC_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_BINARY_TOOL')
        self.assertEqual(r["binding"], 'rsync_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(373, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(373, {"canonical_name": "OTHER"})
    def test_cap_0374(self):
        r = tranche.run(374, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CAS_SYNC')
        self.assertEqual(r["kind"], 'SYNC_ENGINE')
        self.assertEqual(r["binding"], 'cas_sync')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(374, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(374, {"canonical_name": "OTHER"})
    def test_cap_0375(self):
        r = tranche.run(375, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RESUMABLE_FETCH')
        self.assertEqual(r["kind"], 'NETWORK_ENGINE')
        self.assertEqual(r["binding"], 'resumable_fetch')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(375, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(375, {"canonical_name": "OTHER"})
    def test_cap_0376(self):
        r = tranche.run(376, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BANDWIDTH_BUDGET')
        self.assertEqual(r["kind"], 'RESOURCE_POLICY')
        self.assertEqual(r["binding"], 'bandwidth_budget')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(376, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(376, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
