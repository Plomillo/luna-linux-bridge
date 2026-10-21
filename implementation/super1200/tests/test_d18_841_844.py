#!/usr/bin/env python3
"""Negative tests for D18 841-844. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_841_844 as tranche


class D18Tranche841844Tests(unittest.TestCase):
    def test_cap_0841(self):
        r = tranche.run(841, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_INCREMENTALITY_ENGINE')
        self.assertEqual(r["kind"], 'OPTIMIZATION_ENGINE')
        self.assertEqual(r["binding"], 'maintenance_incrementality_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(841, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(841, {"canonical_name": "OTHER"})
    def test_cap_0842(self):
        r = tranche.run(842, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTENANCE_CACHE')
        self.assertEqual(r["kind"], 'CACHE')
        self.assertEqual(r["binding"], 'maintenance_cache')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(842, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(842, {"canonical_name": "OTHER"})
    def test_cap_0843(self):
        r = tranche.run(843, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'VALIDATION_CACHE')
        self.assertEqual(r["kind"], 'CACHE')
        self.assertEqual(r["binding"], 'validation_cache')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(843, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(843, {"canonical_name": "OTHER"})
    def test_cap_0844(self):
        r = tranche.run(844, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CERTIFICATION_CACHE')
        self.assertEqual(r["kind"], 'EVIDENCE_CACHE')
        self.assertEqual(r["binding"], 'certification_cache')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(844, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(844, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
