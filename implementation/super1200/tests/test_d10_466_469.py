#!/usr/bin/env python3
"""Negative tests for D10 466-469. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d10_466_469 as tranche


class D10Tranche466469Tests(unittest.TestCase):
    def test_cap_0466(self):
        r = tranche.run(466, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_ADAPTER_GENERATOR')
        self.assertEqual(r["kind"], 'FACTORY_TOOL')
        self.assertEqual(r["binding"], 'engine_adapter_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(466, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(466, {"canonical_name": "OTHER"})
    def test_cap_0467(self):
        r = tranche.run(467, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_SANDBOX')
        self.assertEqual(r["kind"], 'SANDBOX')
        self.assertEqual(r["binding"], 'engine_sandbox')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(467, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(467, {"canonical_name": "OTHER"})
    def test_cap_0468(self):
        r = tranche.run(468, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_BENCHMARK_TEMPLATE')
        self.assertEqual(r["kind"], 'TEMPLATE')
        self.assertEqual(r["binding"], 'engine_benchmark_template')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(468, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(468, {"canonical_name": "OTHER"})
    def test_cap_0469(self):
        r = tranche.run(469, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_PROVENANCE_TEMPLATE')
        self.assertEqual(r["kind"], 'TEMPLATE')
        self.assertEqual(r["binding"], 'engine_provenance_template')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(469, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(469, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
