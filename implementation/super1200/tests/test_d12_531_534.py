#!/usr/bin/env python3
"""Negative tests for D12 531-534. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_531_534 as tranche


class D12Tranche531534Tests(unittest.TestCase):
    def test_cap_0531(self):
        r = tranche.run(531, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CHAOS_ENGINEERING_FABRIC')
        self.assertEqual(r["kind"], 'RESILIENCE_FABRIC')
        self.assertEqual(r["binding"], 'chaos_engineering_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(531, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(531, {"canonical_name": "OTHER"})
    def test_cap_0532(self):
        r = tranche.run(532, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FAULT_INJECTION')
        self.assertEqual(r["kind"], 'TEST_ENGINE')
        self.assertEqual(r["binding"], 'fault_injection')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(532, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(532, {"canonical_name": "OTHER"})
    def test_cap_0533(self):
        r = tranche.run(533, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NETWORK_PARTITION_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'network_partition_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(533, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(533, {"canonical_name": "OTHER"})
    def test_cap_0534(self):
        r = tranche.run(534, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DISK_FAILURE_SIMULATOR')
        self.assertEqual(r["kind"], 'SIMULATOR')
        self.assertEqual(r["binding"], 'disk_failure_simulator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(534, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(534, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
