#!/usr/bin/env python3
"""Negative tests for D18 801-804. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_801_804 as tranche


class D18Tranche801804Tests(unittest.TestCase):
    def test_cap_0801(self):
        r = tranche.run(801, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPATIBILITY_FABRIC')
        self.assertEqual(r["kind"], 'COMPATIBILITY_FABRIC')
        self.assertEqual(r["binding"], 'compatibility_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(801, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(801, {"canonical_name": "OTHER"})
    def test_cap_0802(self):
        r = tranche.run(802, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BACKWARD_COMPATIBILITY_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'backward_compatibility_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(802, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(802, {"canonical_name": "OTHER"})
    def test_cap_0803(self):
        r = tranche.run(803, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FORWARD_COMPATIBILITY_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'forward_compatibility_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(803, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(803, {"canonical_name": "OTHER"})
    def test_cap_0804(self):
        r = tranche.run(804, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ROUND_TRIP_PRESERVATION_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'round_trip_preservation_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(804, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(804, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
