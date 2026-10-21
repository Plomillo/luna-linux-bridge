#!/usr/bin/env python3
"""Negative tests for D18 761-764. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_761_764 as tranche


class D18Tranche761764Tests(unittest.TestCase):
    def test_cap_0761(self):
        r = tranche.run(761, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_FABRIC')
        self.assertEqual(r["kind"], 'MAINTENANCE_FABRIC')
        self.assertEqual(r["binding"], 'maintenance_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(761, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(761, {"canonical_name": "OTHER"})
    def test_cap_0762(self):
        r = tranche.run(762, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'maintenance_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(762, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(762, {"canonical_name": "OTHER"})
    def test_cap_0763(self):
        r = tranche.run(763, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTAINER_INTERFACE')
        self.assertEqual(r["kind"], 'INTERFACE')
        self.assertEqual(r["binding"], 'maintainer_interface')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(763, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(763, {"canonical_name": "OTHER"})
    def test_cap_0764(self):
        r = tranche.run(764, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_STATE_MACHINE')
        self.assertEqual(r["kind"], 'STATE_MACHINE')
        self.assertEqual(r["binding"], 'maintenance_state_machine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(764, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(764, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
