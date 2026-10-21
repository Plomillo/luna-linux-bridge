#!/usr/bin/env python3
"""Negative tests for D10 458-461. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d10_458_461 as tranche


class D10Tranche458461Tests(unittest.TestCase):
    def test_cap_0458(self):
        r = tranche.run(458, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LANGUAGE_TEST_SUITE')
        self.assertEqual(r["kind"], 'TEST_SUITE')
        self.assertEqual(r["binding"], 'language_test_suite')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(458, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(458, {"canonical_name": "OTHER"})
    def test_cap_0459(self):
        r = tranche.run(459, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SEMANTICS_SPEC')
        self.assertEqual(r["kind"], 'NORMATIVE_SPEC')
        self.assertEqual(r["binding"], 'semantics_spec')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(459, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(459, {"canonical_name": "OTHER"})
    def test_cap_0460(self):
        r = tranche.run(460, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FORMAL_SEMANTICS_PROVIDER')
        self.assertEqual(r["kind"], 'FORMAL_PROVIDER')
        self.assertEqual(r["binding"], 'formal_semantics_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(460, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(460, {"canonical_name": "OTHER"})
    def test_cap_0461(self):
        r = tranche.run(461, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ENGINE_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'engine_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(461, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(461, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
