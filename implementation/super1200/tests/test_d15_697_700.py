#!/usr/bin/env python3
"""Negative tests for D15 697-700. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d15_697_700 as tranche


class D15Tranche697700Tests(unittest.TestCase):
    def test_cap_0697(self):
        r = tranche.run(697, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OPTIMIZATION_CAUSALITY_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'optimization_causality_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(697, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(697, {"canonical_name": "OTHER"})
    def test_cap_0698(self):
        r = tranche.run(698, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OPTIMIZATION_ROLLBACK')
        self.assertEqual(r["kind"], 'RECOVERY_PATTERN')
        self.assertEqual(r["binding"], 'optimization_rollback')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(698, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(698, {"canonical_name": "OTHER"})
    def test_cap_0699(self):
        r = tranche.run(699, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HARDWARE_SERVICE_RECOMMENDER')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'hardware_service_recommender')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(699, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(699, {"canonical_name": "OTHER"})
    def test_cap_0700(self):
        r = tranche.run(700, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DO_NOT_FAKE_REPAIR_CONTROL')
        self.assertEqual(r["kind"], 'SAFETY_GATE')
        self.assertEqual(r["binding"], 'do_not_fake_repair_control')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(700, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(700, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
