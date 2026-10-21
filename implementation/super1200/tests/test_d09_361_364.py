#!/usr/bin/env python3
"""Negative tests for D09 361-364. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_361_364 as tranche


class D09Tranche361364Tests(unittest.TestCase):
    def test_cap_0361(self):
        r = tranche.run(361, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REMOTE_DATASET_INSPECTOR')
        self.assertEqual(r["kind"], 'DATA_ENGINE')
        self.assertEqual(r["binding"], 'remote_dataset_inspector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(361, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(361, {"canonical_name": "OTHER"})
    def test_cap_0362(self):
        r = tranche.run(362, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HTTP_RANGE_READER')
        self.assertEqual(r["kind"], 'NETWORK_LIBRARY')
        self.assertEqual(r["binding"], 'http_range_reader')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(362, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(362, {"canonical_name": "OTHER"})
    def test_cap_0363(self):
        r = tranche.run(363, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'S3_RANGE_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_SERVICE_ADAPTER')
        self.assertEqual(r["binding"], 's3_range_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(363, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(363, {"canonical_name": "OTHER"})
    def test_cap_0364(self):
        r = tranche.run(364, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PARQUET_PUSHDOWN')
        self.assertEqual(r["kind"], 'DATA_ENGINE')
        self.assertEqual(r["binding"], 'parquet_pushdown')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(364, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(364, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
