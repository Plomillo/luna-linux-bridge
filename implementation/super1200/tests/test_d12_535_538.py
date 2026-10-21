#!/usr/bin/env python3
"""Negative tests for D12 535-538. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_535_538 as tranche


class D12Tranche535538Tests(unittest.TestCase):
    def test_cap_0535(self):
        r = tranche.run(535, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MEMORY_PRESSURE_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'memory_pressure_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(535, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(535, {"canonical_name": "OTHER"})
    def test_cap_0536(self):
        r = tranche.run(536, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CPU_PRESSURE_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'cpu_pressure_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(536, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(536, {"canonical_name": "OTHER"})
    def test_cap_0537(self):
        r = tranche.run(537, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLOCK_DRIFT_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'clock_drift_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(537, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(537, {"canonical_name": "OTHER"})
    def test_cap_0538(self):
        r = tranche.run(538, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEPENDENCY_FAILURE_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'dependency_failure_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(538, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(538, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
