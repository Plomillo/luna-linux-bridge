#!/usr/bin/env python3
"""Negative tests for D08 349-352. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_349_352 as tranche


class D08Tranche349352Tests(unittest.TestCase):
    def test_cap_0349(self):
        r = tranche.run(349, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CHUNKED_ARCHIVE_ENGINE')
        self.assertEqual(r["kind"], 'ARCHIVE_ENGINE')
        self.assertEqual(r["binding"], 'chunked_archive_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(349, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(349, {"canonical_name": "OTHER"})
    def test_cap_0350(self):
        r = tranche.run(350, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STREAMING_COMPRESSION')
        self.assertEqual(r["kind"], 'COMPRESSION_ENGINE')
        self.assertEqual(r["binding"], 'streaming_compression')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(350, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(350, {"canonical_name": "OTHER"})
    def test_cap_0351(self):
        r = tranche.run(351, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SEEKABLE_COMPRESSION')
        self.assertEqual(r["kind"], 'COMPRESSION_ENGINE')
        self.assertEqual(r["binding"], 'seekable_compression')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(351, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(351, {"canonical_name": "OTHER"})
    def test_cap_0352(self):
        r = tranche.run(352, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEDUPE_BEFORE_COMPRESSION')
        self.assertEqual(r["kind"], 'DATA_ENGINE')
        self.assertEqual(r["binding"], 'dedupe_before_compression')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(352, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(352, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
