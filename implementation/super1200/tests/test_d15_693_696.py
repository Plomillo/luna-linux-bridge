#!/usr/bin/env python3
"""Negative tests for D15 693-696. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d15_693_696 as tranche


class D15Tranche693696Tests(unittest.TestCase):
    def test_cap_0693(self):
        r = tranche.run(693, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BACKGROUND_ACTIVITY_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'background_activity_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(693, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(693, {"canonical_name": "OTHER"})
    def test_cap_0694(self):
        r = tranche.run(694, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LATENCY_DIAGNOSTICS')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'latency_diagnostics')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(694, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(694, {"canonical_name": "OTHER"})
    def test_cap_0695(self):
        r = tranche.run(695, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RESOURCE_LEAK_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'resource_leak_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(695, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(695, {"canonical_name": "OTHER"})
    def test_cap_0696(self):
        r = tranche.run(696, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BEFORE_AFTER_BENCHMARK_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'before_after_benchmark_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(696, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(696, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
