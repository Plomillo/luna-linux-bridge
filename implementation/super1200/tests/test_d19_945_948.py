#!/usr/bin/env python3
"""Negative tests for D19 945-948. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_945_948 as tranche


class D19Tranche945948Tests(unittest.TestCase):
    def test_cap_0945(self):
        r = tranche.run(945, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_MULTI_SCANNER')
        self.assertEqual(r["kind"], 'ORCHESTRATION_ENGINE')
        self.assertEqual(r["binding"], 'luna_defender_multi_scanner')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(945, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(945, {"canonical_name": "OTHER"})
    def test_cap_0946(self):
        r = tranche.run(946, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_CONSENSUS')
        self.assertEqual(r["kind"], 'CONSENSUS_ENGINE')
        self.assertEqual(r["binding"], 'luna_defender_consensus')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(946, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(946, {"canonical_name": "OTHER"})
    def test_cap_0947(self):
        r = tranche.run(947, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_MACHINE_BASELINE')
        self.assertEqual(r["kind"], 'BASELINE')
        self.assertEqual(r["binding"], 'luna_defender_machine_baseline')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(947, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(947, {"canonical_name": "OTHER"})
    def test_cap_0948(self):
        r = tranche.run(948, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_REPOSITORY_BASELINE')
        self.assertEqual(r["kind"], 'BASELINE')
        self.assertEqual(r["binding"], 'luna_defender_repository_baseline')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(948, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(948, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
