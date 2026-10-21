#!/usr/bin/env python3
"""Negative tests for D16 717-720. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d16_717_720 as tranche


class D16Tranche717720Tests(unittest.TestCase):
    def test_cap_0717(self):
        r = tranche.run(717, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GAMESCOPE_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_GRAPHICS_RUNTIME')
        self.assertEqual(r["binding"], 'gamescope_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(717, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(717, {"canonical_name": "OTHER"})
    def test_cap_0718(self):
        r = tranche.run(718, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GAME_REGRESSION_BENCHMARK')
        self.assertEqual(r["kind"], 'BENCHMARK_ENGINE')
        self.assertEqual(r["binding"], 'game_regression_benchmark')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(718, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(718, {"canonical_name": "OTHER"})
    def test_cap_0719(self):
        r = tranche.run(719, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPATIBILITY_PATCH_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'compatibility_patch_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(719, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(719, {"canonical_name": "OTHER"})
    def test_cap_0720(self):
        r = tranche.run(720, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'WINE_EVOLUTION_LAB')
        self.assertEqual(r["kind"], 'LAB')
        self.assertEqual(r["binding"], 'wine_evolution_lab')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(720, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(720, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
