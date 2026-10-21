#!/usr/bin/env python3
"""Negative tests for D20 973-976. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d20_973_976 as tranche


class D20Tranche973976Tests(unittest.TestCase):
    def test_cap_0973(self):
        r = tranche.run(973, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STATIC_TRIAGE_ENGINE')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'static_triage_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(973, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(973, {"canonical_name": "OTHER"})
    def test_cap_0974(self):
        r = tranche.run(974, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BEHAVIORAL_SANDBOX')
        self.assertEqual(r["kind"], 'SANDBOX')
        self.assertEqual(r["binding"], 'behavioral_sandbox')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(974, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(974, {"canonical_name": "OTHER"})
    def test_cap_0975(self):
        r = tranche.run(975, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EPHEMERAL_ANALYSIS_VM')
        self.assertEqual(r["kind"], 'VM_PROVIDER_PATTERN')
        self.assertEqual(r["binding"], 'ephemeral_analysis_vm')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(975, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(975, {"canonical_name": "OTHER"})
    def test_cap_0976(self):
        r = tranche.run(976, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NETWORK_SIMULATION_SANDBOX')
        self.assertEqual(r["kind"], 'SANDBOX')
        self.assertEqual(r["binding"], 'network_simulation_sandbox')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(976, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(976, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
