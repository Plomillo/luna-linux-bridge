#!/usr/bin/env python3
"""Negative tests for D18 845-848. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_845_848 as tranche


class D18Tranche845848Tests(unittest.TestCase):
    def test_cap_0845(self):
        r = tranche.run(845, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CAUSAL_CACHE_INVALIDATION')
        self.assertEqual(r["kind"], 'INVALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'causal_cache_invalidation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(845, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(845, {"canonical_name": "OTHER"})
    def test_cap_0846(self):
        r = tranche.run(846, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TEST_RESULT_REUSE_ENGINE')
        self.assertEqual(r["kind"], 'EVIDENCE_REUSE_ENGINE')
        self.assertEqual(r["binding"], 'test_result_reuse_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(846, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(846, {"canonical_name": "OTHER"})
    def test_cap_0847(self):
        r = tranche.run(847, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BUILD_RESULT_REUSE_ENGINE')
        self.assertEqual(r["kind"], 'CACHE_ENGINE')
        self.assertEqual(r["binding"], 'build_result_reuse_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(847, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(847, {"canonical_name": "OTHER"})
    def test_cap_0848(self):
        r = tranche.run(848, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DIAGNOSTIC_RESULT_REUSE')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REUSE_ENGINE')
        self.assertEqual(r["binding"], 'diagnostic_result_reuse')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(848, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(848, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
