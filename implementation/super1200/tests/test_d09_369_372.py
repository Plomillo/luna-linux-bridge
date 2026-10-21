#!/usr/bin/env python3
"""Negative tests for D09 369-372. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_369_372 as tranche


class D09Tranche369372Tests(unittest.TestCase):
    def test_cap_0369(self):
        r = tranche.run(369, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONTENT_DEFINED_CHUNKING')
        self.assertEqual(r["kind"], 'DATA_ENGINE')
        self.assertEqual(r["binding"], 'content_defined_chunking')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(369, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(369, {"canonical_name": "OTHER"})
    def test_cap_0370(self):
        r = tranche.run(370, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MERKLE_CHUNK_STORE')
        self.assertEqual(r["kind"], 'CONTENT_STORE')
        self.assertEqual(r["binding"], 'merkle_chunk_store')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(370, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(370, {"canonical_name": "OTHER"})
    def test_cap_0371(self):
        r = tranche.run(371, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DISTRIBUTED_CONTENT_CACHE')
        self.assertEqual(r["kind"], 'CACHE_FABRIC')
        self.assertEqual(r["binding"], 'distributed_content_cache')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(371, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(371, {"canonical_name": "OTHER"})
    def test_cap_0372(self):
        r = tranche.run(372, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DELTA_TRANSFER')
        self.assertEqual(r["kind"], 'TRANSPORT_ENGINE')
        self.assertEqual(r["binding"], 'delta_transfer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(372, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(372, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
