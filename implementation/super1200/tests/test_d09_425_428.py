#!/usr/bin/env python3
"""Negative tests for D09 425-428. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_425_428 as tranche


class D09Tranche425428Tests(unittest.TestCase):
    def test_cap_0425(self):
        r = tranche.run(425, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DRIVER_COMPATIBILITY_ENGINE')
        self.assertEqual(r["kind"], 'COMPATIBILITY_ENGINE')
        self.assertEqual(r["binding"], 'driver_compatibility_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(425, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(425, {"canonical_name": "OTHER"})
    def test_cap_0426(self):
        r = tranche.run(426, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURE_UPDATE_FABRIC')
        self.assertEqual(r["kind"], 'SECURITY_FABRIC')
        self.assertEqual(r["binding"], 'secure_update_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(426, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(426, {"canonical_name": "OTHER"})
    def test_cap_0427(self):
        r = tranche.run(427, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TUF_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_SECURITY_LIBRARY')
        self.assertEqual(r["binding"], 'tuf_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(427, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(427, {"canonical_name": "OTHER"})
    def test_cap_0428(self):
        r = tranche.run(428, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ROLLBACK_PROTECTION')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'rollback_protection')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(428, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(428, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
