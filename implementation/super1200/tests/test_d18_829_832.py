#!/usr/bin/env python3
"""Negative tests for D18 829-832. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_829_832 as tranche


class D18Tranche829832Tests(unittest.TestCase):
    def test_cap_0829(self):
        r = tranche.run(829, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PATCH_EQUIVALENCE_CHECKER')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'patch_equivalence_checker')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(829, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(829, {"canonical_name": "OTHER"})
    def test_cap_0830(self):
        r = tranche.run(830, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_PREFLIGHT')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'update_preflight')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(830, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(830, {"canonical_name": "OTHER"})
    def test_cap_0831(self):
        r = tranche.run(831, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'update_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(831, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(831, {"canonical_name": "OTHER"})
    def test_cap_0832(self):
        r = tranche.run(832, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_CANARY')
        self.assertEqual(r["kind"], 'DEPLOYMENT_ENGINE')
        self.assertEqual(r["binding"], 'update_canary')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(832, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(832, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
