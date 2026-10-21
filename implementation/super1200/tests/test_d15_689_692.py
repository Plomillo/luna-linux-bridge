#!/usr/bin/env python3
"""Negative tests for D15 689-692. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d15_689_692 as tranche


class D15Tranche689692Tests(unittest.TestCase):
    def test_cap_0689(self):
        r = tranche.run(689, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DRIVER_REPAIR_ENGINE')
        self.assertEqual(r["kind"], 'REPAIR_ENGINE')
        self.assertEqual(r["binding"], 'driver_repair_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(689, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(689, {"canonical_name": "OTHER"})
    def test_cap_0690(self):
        r = tranche.run(690, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FIRMWARE_UPDATE_ORCHESTRATOR')
        self.assertEqual(r["kind"], 'UPDATE_ORCHESTRATOR')
        self.assertEqual(r["binding"], 'firmware_update_orchestrator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(690, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(690, {"canonical_name": "OTHER"})
    def test_cap_0691(self):
        r = tranche.run(691, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PERFORMANCE_REGRESSION_DIAGNOSTICS')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'performance_regression_diagnostics')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(691, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(691, {"canonical_name": "OTHER"})
    def test_cap_0692(self):
        r = tranche.run(692, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BLOAT_ATTRIBUTION_ENGINE')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'bloat_attribution_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(692, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(692, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
