#!/usr/bin/env python3
"""Negative tests for D22 1189-1192. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1189_1192 as tranche


class D22Tranche11891192Tests(unittest.TestCase):
    def test_cap_1189(self):
        r = tranche.run(1189, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREVENTION_SIMULATION_ENGINE')
        self.assertEqual(r["kind"], 'DEFENSIVE_SIMULATION_ENGINE')
        self.assertEqual(r["binding"], 'prevention_simulation_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1189, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1189, {"canonical_name": "OTHER"})
    def test_cap_1190(self):
        r = tranche.run(1190, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREVENTIVE_SECURITY_POLICY_SYNTHESIS')
        self.assertEqual(r["kind"], 'SECURITY_POLICY_ENGINE')
        self.assertEqual(r["binding"], 'preventive_security_policy_synthesis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1190, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1190, {"canonical_name": "OTHER"})
    def test_cap_1191(self):
        r = tranche.run(1191, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ATTACK_SURFACE_MOTIVATION_LINKER')
        self.assertEqual(r["kind"], 'DEFENSIVE_RISK_GRAPH')
        self.assertEqual(r["binding"], 'attack_surface_motivation_linker')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1191, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1191, {"canonical_name": "OTHER"})
    def test_cap_1192(self):
        r = tranche.run(1192, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREDICTIVE_THREAT_HYPOTHESIS')
        self.assertEqual(r["kind"], 'DEFENSIVE_PREDICTIVE_ENGINE')
        self.assertEqual(r["binding"], 'predictive_threat_hypothesis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1192, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1192, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
