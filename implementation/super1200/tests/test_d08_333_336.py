#!/usr/bin/env python3
"""Negative tests for D08 333-336. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_333_336 as tranche


class D08Tranche333336Tests(unittest.TestCase):
    def test_cap_0333(self):
        r = tranche.run(333, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENTROPY_ESTIMATOR')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'entropy_estimator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(333, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(333, {"canonical_name": "OTHER"})
    def test_cap_0334(self):
        r = tranche.run(334, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPRESSIBILITY_PROBE')
        self.assertEqual(r["kind"], 'BENCHMARK_ENGINE')
        self.assertEqual(r["binding"], 'compressibility_probe')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(334, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(334, {"canonical_name": "OTHER"})
    def test_cap_0335(self):
        r = tranche.run(335, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPRESSION_BENCHMARK_ENGINE')
        self.assertEqual(r["kind"], 'BENCHMARK_ENGINE')
        self.assertEqual(r["binding"], 'compression_benchmark_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(335, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(335, {"canonical_name": "OTHER"})
    def test_cap_0336(self):
        r = tranche.run(336, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ZSTD_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_LIBRARY_TOOL')
        self.assertEqual(r["binding"], 'zstd_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(336, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(336, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
