#!/usr/bin/env python3
"""Negative tests for D15 677-680. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d15_677_680 as tranche


class D15Tranche677680Tests(unittest.TestCase):
    def test_cap_0677(self):
        r = tranche.run(677, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PERIPHERAL_DIAGNOSTICS')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_FABRIC')
        self.assertEqual(r["binding"], 'peripheral_diagnostics')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(677, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(677, {"canonical_name": "OTHER"})
    def test_cap_0678(self):
        r = tranche.run(678, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MACHINE_BASELINE_PROFILE')
        self.assertEqual(r["kind"], 'BASELINE')
        self.assertEqual(r["binding"], 'machine_baseline_profile')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(678, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(678, {"canonical_name": "OTHER"})
    def test_cap_0679(self):
        r = tranche.run(679, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MACHINE_HEALTH_DRIFT')
        self.assertEqual(r["kind"], 'DRIFT_ENGINE')
        self.assertEqual(r["binding"], 'machine_health_drift')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(679, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(679, {"canonical_name": "OTHER"})
    def test_cap_0680(self):
        r = tranche.run(680, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MACHINE_PROGNOSTICS_ENGINE')
        self.assertEqual(r["kind"], 'ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'machine_prognostics_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(680, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(680, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
