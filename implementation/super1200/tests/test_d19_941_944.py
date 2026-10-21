#!/usr/bin/env python3
"""Negative tests for D19 941-944. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_941_944 as tranche


class D19Tranche941944Tests(unittest.TestCase):
    def test_cap_0941(self):
        r = tranche.run(941, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER')
        self.assertEqual(r["kind"], 'DEFENSIVE_SECURITY_SYSTEM')
        self.assertEqual(r["binding"], 'luna_defender')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(941, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(941, {"canonical_name": "OTHER"})
    def test_cap_0942(self):
        r = tranche.run(942, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_RULE_ENGINE')
        self.assertEqual(r["kind"], 'RULE_ENGINE')
        self.assertEqual(r["binding"], 'luna_defender_rule_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(942, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(942, {"canonical_name": "OTHER"})
    def test_cap_0943(self):
        r = tranche.run(943, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_BEHAVIOR_ENGINE')
        self.assertEqual(r["kind"], 'DEFENSIVE_ENGINE')
        self.assertEqual(r["binding"], 'luna_defender_behavior_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(943, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(943, {"canonical_name": "OTHER"})
    def test_cap_0944(self):
        r = tranche.run(944, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LUNA_DEFENDER_REPUTATION_ENGINE')
        self.assertEqual(r["kind"], 'EVIDENCE_ENGINE')
        self.assertEqual(r["binding"], 'luna_defender_reputation_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(944, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(944, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
