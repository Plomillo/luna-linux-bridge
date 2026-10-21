#!/usr/bin/env python3
"""Negative tests for D12 563-566. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_563_566 as tranche


class D12Tranche563566Tests(unittest.TestCase):
    def test_cap_0563(self):
        r = tranche.run(563, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SCHEMA_COMPATIBILITY')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'schema_compatibility')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(563, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(563, {"canonical_name": "OTHER"})
    def test_cap_0564(self):
        r = tranche.run(564, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'API_VERSIONING')
        self.assertEqual(r["kind"], 'API_POLICY')
        self.assertEqual(r["binding"], 'api_versioning')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(564, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(564, {"canonical_name": "OTHER"})
    def test_cap_0565(self):
        r = tranche.run(565, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'API_CONTRACT_TESTING')
        self.assertEqual(r["kind"], 'TEST_ENGINE')
        self.assertEqual(r["binding"], 'api_contract_testing')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(565, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(565, {"canonical_name": "OTHER"})
    def test_cap_0566(self):
        r = tranche.run(566, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'API_FUZZING')
        self.assertEqual(r["kind"], 'TEST_ENGINE')
        self.assertEqual(r["binding"], 'api_fuzzing')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(566, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(566, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
