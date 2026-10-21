#!/usr/bin/env python3
"""Negative tests for D09 429-432. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_429_432 as tranche


class D09Tranche429432Tests(unittest.TestCase):
    def test_cap_0429(self):
        r = tranche.run(429, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FREEZE_ATTACK_PROTECTION')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'freeze_attack_protection')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(429, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(429, {"canonical_name": "OTHER"})
    def test_cap_0430(self):
        r = tranche.run(430, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MIRROR_COMPROMISE_PROTECTION')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'mirror_compromise_protection')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(430, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(430, {"canonical_name": "OTHER"})
    def test_cap_0431(self):
        r = tranche.run(431, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_METADATA_SIGNATURES')
        self.assertEqual(r["kind"], 'SIGNATURE_ENGINE')
        self.assertEqual(r["binding"], 'update_metadata_signatures')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(431, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(431, {"canonical_name": "OTHER"})
    def test_cap_0432(self):
        r = tranche.run(432, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OFFLINE_ROOT_KEYS')
        self.assertEqual(r["kind"], 'KEY_CUSTODY_PATTERN')
        self.assertEqual(r["binding"], 'offline_root_keys')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(432, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(432, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
