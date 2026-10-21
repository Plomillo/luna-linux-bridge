#!/usr/bin/env python3
"""Negative tests for D07 271-274. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_271_274 as tranche


class D07Tranche271274Tests(unittest.TestCase):
    def test_cap_0271(self):
        r = tranche.run(271, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SCIPY_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_LIBRARY')
        self.assertEqual(r["binding"], 'scipy_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(271, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(271, {"canonical_name": "OTHER"})
    def test_cap_0272(self):
        r = tranche.run(272, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STATSMODELS_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_LIBRARY')
        self.assertEqual(r["binding"], 'statsmodels_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(272, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(272, {"canonical_name": "OTHER"})
    def test_cap_0273(self):
        r = tranche.run(273, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BAYESIAN_ENGINE')
        self.assertEqual(r["kind"], 'ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'bayesian_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(273, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(273, {"canonical_name": "OTHER"})
    def test_cap_0274(self):
        r = tranche.run(274, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PYMC_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_LIBRARY')
        self.assertEqual(r["binding"], 'pymc_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(274, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(274, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
