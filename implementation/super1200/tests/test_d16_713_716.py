#!/usr/bin/env python3
"""Negative tests for D16 713-716. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d16_713_716 as tranche


class D16Tranche713716Tests(unittest.TestCase):
    def test_cap_0713(self):
        r = tranche.run(713, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CPU_GPU_BOTTLENECK_CLASSIFIER')
        self.assertEqual(r["kind"], 'CLASSIFIER')
        self.assertEqual(r["binding"], 'cpu_gpu_bottleneck_classifier')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(713, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(713, {"canonical_name": "OTHER"})
    def test_cap_0714(self):
        r = tranche.run(714, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GAME_MEMORY_ANALYZER')
        self.assertEqual(r["kind"], 'PERFORMANCE_ANALYZER')
        self.assertEqual(r["binding"], 'game_memory_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(714, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(714, {"canonical_name": "OTHER"})
    def test_cap_0715(self):
        r = tranche.run(715, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GAME_IO_ANALYZER')
        self.assertEqual(r["kind"], 'PERFORMANCE_ANALYZER')
        self.assertEqual(r["binding"], 'game_io_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(715, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(715, {"canonical_name": "OTHER"})
    def test_cap_0716(self):
        r = tranche.run(716, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GAME_CONFIGURATION_OPTIMIZER')
        self.assertEqual(r["kind"], 'OPTIMIZATION_ENGINE')
        self.assertEqual(r["binding"], 'game_configuration_optimizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(716, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(716, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
