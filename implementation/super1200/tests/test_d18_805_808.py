#!/usr/bin/env python3
"""Negative tests for D18 805-808. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_805_808 as tranche


class D18Tranche805808Tests(unittest.TestCase):
    def test_cap_0805(self):
        r = tranche.run(805, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'VERSION_SKEW_POLICY')
        self.assertEqual(r["kind"], 'POLICY')
        self.assertEqual(r["binding"], 'version_skew_policy')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(805, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(805, {"canonical_name": "OTHER"})
    def test_cap_0806(self):
        r = tranche.run(806, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPATIBILITY_MATRIX')
        self.assertEqual(r["kind"], 'MATRIX/REGISTRY')
        self.assertEqual(r["binding"], 'compatibility_matrix')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(806, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(806, {"canonical_name": "OTHER"})
    def test_cap_0807(self):
        r = tranche.run(807, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEPRECATION_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'deprecation_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(807, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(807, {"canonical_name": "OTHER"})
    def test_cap_0808(self):
        r = tranche.run(808, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEPRECATION_CLOCK')
        self.assertEqual(r["kind"], 'POLICY_ENGINE')
        self.assertEqual(r["binding"], 'deprecation_clock')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(808, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(808, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
