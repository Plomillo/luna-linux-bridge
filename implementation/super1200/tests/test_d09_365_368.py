#!/usr/bin/env python3
"""Negative tests for D09 365-368. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_365_368 as tranche


class D09Tranche365368Tests(unittest.TestCase):
    def test_cap_0365(self):
        r = tranche.run(365, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REMOTE_ARROW')
        self.assertEqual(r["kind"], 'DATA_INTERFACE')
        self.assertEqual(r["binding"], 'remote_arrow')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(365, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(365, {"canonical_name": "OTHER"})
    def test_cap_0366(self):
        r = tranche.run(366, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STREAMING_DATASET_PROVIDER')
        self.assertEqual(r["kind"], 'DATA_PROVIDER_INTERFACE')
        self.assertEqual(r["binding"], 'streaming_dataset_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(366, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(366, {"canonical_name": "OTHER"})
    def test_cap_0367(self):
        r = tranche.run(367, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PARTIAL_TAR_READER')
        self.assertEqual(r["kind"], 'ARCHIVE_LIBRARY')
        self.assertEqual(r["binding"], 'partial_tar_reader')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(367, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(367, {"canonical_name": "OTHER"})
    def test_cap_0368(self):
        r = tranche.run(368, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SHARD_INDEX')
        self.assertEqual(r["kind"], 'INDEX')
        self.assertEqual(r["binding"], 'shard_index')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(368, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(368, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
