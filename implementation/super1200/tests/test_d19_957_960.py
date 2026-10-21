#!/usr/bin/env python3
"""Negative tests for D19 957-960. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_957_960 as tranche


class D19Tranche957960Tests(unittest.TestCase):
    def test_cap_0957(self):
        r = tranche.run(957, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_RULE_ROLLBACK')
        self.assertEqual(r["kind"], 'RECOVERY_ENGINE')
        self.assertEqual(r["binding"], 'luna_defender_rule_rollback')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(957, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(957, {"canonical_name": "OTHER"})
    def test_cap_0958(self):
        r = tranche.run(958, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_INDEPENDENT_VALIDATION')
        self.assertEqual(r["kind"], 'G23_INTERFACE')
        self.assertEqual(r["binding"], 'luna_defender_independent_validation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(958, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(958, {"canonical_name": "OTHER"})
    def test_cap_0959(self):
        r = tranche.run(959, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_CERTIFICATION')
        self.assertEqual(r["kind"], 'G24_INTERFACE')
        self.assertEqual(r["binding"], 'luna_defender_certification')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(959, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(959, {"canonical_name": "OTHER"})
    def test_cap_0960(self):
        r = tranche.run(960, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_EVOLUTION_ENGINE')
        self.assertEqual(r["kind"], 'EVOLUTION_ENGINE')
        self.assertEqual(r["binding"], 'luna_defender_evolution_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(960, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(960, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
