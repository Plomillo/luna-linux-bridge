#!/usr/bin/env python3
"""Negative tests for D19 953-956. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_953_956 as tranche


class D19Tranche953956Tests(unittest.TestCase):
    def test_cap_0953(self):
        r = tranche.run(953, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_FALSE_NEGATIVE_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'luna_defender_false_negative_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(953, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(953, {"canonical_name": "OTHER"})
    def test_cap_0954(self):
        r = tranche.run(954, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_ADVERSARIAL_EVALUATION')
        self.assertEqual(r["kind"], 'DEFENSIVE_TEST_ENGINE')
        self.assertEqual(r["binding"], 'luna_defender_adversarial_evaluation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(954, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(954, {"canonical_name": "OTHER"})
    def test_cap_0955(self):
        r = tranche.run(955, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_SELF_AUDIT')
        self.assertEqual(r["kind"], 'AUDIT_ENGINE')
        self.assertEqual(r["binding"], 'luna_defender_self_audit')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(955, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(955, {"canonical_name": "OTHER"})
    def test_cap_0956(self):
        r = tranche.run(956, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_SELF_UPDATE')
        self.assertEqual(r["kind"], 'UPDATE_ENGINE')
        self.assertEqual(r["binding"], 'luna_defender_self_update')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(956, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(956, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
