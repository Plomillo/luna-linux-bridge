#!/usr/bin/env python3
"""Negative tests for D18 777-780. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_777_780 as tranche


class D18Tranche777780Tests(unittest.TestCase):
    def test_cap_0777(self):
        r = tranche.run(777, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_SLA_ENGINE')
        self.assertEqual(r["kind"], 'POLICY_ENGINE')
        self.assertEqual(r["binding"], 'maintenance_sla_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(777, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(777, {"canonical_name": "OTHER"})
    def test_cap_0778(self):
        r = tranche.run(778, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_HEALTH_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'maintenance_health_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(778, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(778, {"canonical_name": "OTHER"})
    def test_cap_0779(self):
        r = tranche.run(779, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_READINESS_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'maintenance_readiness_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(779, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(779, {"canonical_name": "OTHER"})
    def test_cap_0780(self):
        r = tranche.run(780, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_CERTIFICATION_GATE')
        self.assertEqual(r["kind"], 'CERTIFICATION_READINESS_GATE')
        self.assertEqual(r["binding"], 'maintenance_certification_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(780, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(780, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
