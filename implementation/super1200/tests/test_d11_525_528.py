#!/usr/bin/env python3
"""Negative tests for D11 525-528. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_525_528 as tranche


class D11Tranche525528Tests(unittest.TestCase):
    def test_cap_0525(self):
        r = tranche.run(525, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INTERDISCIPLINARY_SYNTHESIS')
        self.assertEqual(r["kind"], 'SYNTHESIS_ENGINE')
        self.assertEqual(r["binding"], 'interdisciplinary_synthesis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(525, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(525, {"canonical_name": "OTHER"})
    def test_cap_0526(self):
        r = tranche.run(526, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MULTIDISCIPLINARY_PARALLEL_ANALYSIS')
        self.assertEqual(r["kind"], 'ORCHESTRATION_PATTERN')
        self.assertEqual(r["binding"], 'multidisciplinary_parallel_analysis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(526, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(526, {"canonical_name": "OTHER"})
    def test_cap_0527(self):
        r = tranche.run(527, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TRANSDISCIPLINARY_INTEGRATION')
        self.assertEqual(r["kind"], 'SYNTHESIS_ENGINE')
        self.assertEqual(r["binding"], 'transdisciplinary_integration')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(527, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(527, {"canonical_name": "OTHER"})
    def test_cap_0528(self):
        r = tranche.run(528, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONFLICT_OF_METHODS_ENGINE')
        self.assertEqual(r["kind"], 'CONFLICT_ENGINE')
        self.assertEqual(r["binding"], 'conflict_of_methods_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(528, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(528, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
