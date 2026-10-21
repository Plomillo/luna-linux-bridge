#!/usr/bin/env python3
"""Negative tests for D21 1061-1064. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1061_1064 as tranche


class D21Tranche10611064Tests(unittest.TestCase):
    def test_cap_1061(self):
        r = tranche.run(1061, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_FUNCTIONAL_TEST')
        self.assertEqual(r["kind"], 'TEST_ENGINE')
        self.assertEqual(r["binding"], 'substitute_functional_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1061, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1061, {"canonical_name": "OTHER"})
    def test_cap_1062(self):
        r = tranche.run(1062, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_COMPATIBILITY_TEST')
        self.assertEqual(r["kind"], 'TEST_ENGINE')
        self.assertEqual(r["binding"], 'substitute_compatibility_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1062, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1062, {"canonical_name": "OTHER"})
    def test_cap_1063(self):
        r = tranche.run(1063, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_PERFORMANCE_TEST')
        self.assertEqual(r["kind"], 'BENCHMARK')
        self.assertEqual(r["binding"], 'substitute_performance_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1063, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1063, {"canonical_name": "OTHER"})
    def test_cap_1064(self):
        r = tranche.run(1064, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_RESOURCE_TEST')
        self.assertEqual(r["kind"], 'BENCHMARK')
        self.assertEqual(r["binding"], 'substitute_resource_test')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1064, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1064, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
