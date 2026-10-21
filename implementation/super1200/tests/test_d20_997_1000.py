#!/usr/bin/env python3
"""Negative tests for D20 997-1000. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d20_997_1000 as tranche


class D20Tranche9971000Tests(unittest.TestCase):
    def test_cap_0997(self):
        r = tranche.run(997, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DETECTION_RULE_SYNTHESIS')
        self.assertEqual(r["kind"], 'RULE_FACTORY')
        self.assertEqual(r["binding"], 'detection_rule_synthesis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(997, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(997, {"canonical_name": "OTHER"})
    def test_cap_0998(self):
        r = tranche.run(998, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DETECTION_RULE_REGRESSION_LAB')
        self.assertEqual(r["kind"], 'LAB')
        self.assertEqual(r["binding"], 'detection_rule_regression_lab')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(998, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(998, {"canonical_name": "OTHER"})
    def test_cap_0999(self):
        r = tranche.run(999, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INCIDENT_REPLAY_ENGINE')
        self.assertEqual(r["kind"], 'DEFENSIVE_SIMULATOR')
        self.assertEqual(r["binding"], 'incident_replay_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(999, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(999, {"canonical_name": "OTHER"})
    def test_cap_1000(self):
        r = tranche.run(1000, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_IMMUNE_MEMORY')
        self.assertEqual(r["kind"], 'DEFENSIVE_KNOWLEDGE_MEMORY')
        self.assertEqual(r["binding"], 'security_immune_memory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1000, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1000, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
