#!/usr/bin/env python3
"""Negative tests for D08 353-356. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_353_356 as tranche


class D08Tranche353356Tests(unittest.TestCase):
    def test_cap_0353(self):
        r = tranche.run(353, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPRESSION_DICTIONARY_TRAINING')
        self.assertEqual(r["kind"], 'BUILD_TOOL')
        self.assertEqual(r["binding"], 'compression_dictionary_training')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(353, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(353, {"canonical_name": "OTHER"})
    def test_cap_0354(self):
        r = tranche.run(354, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARCHIVE_INTEGRITY_MANIFEST')
        self.assertEqual(r["kind"], 'MANIFEST')
        self.assertEqual(r["binding"], 'archive_integrity_manifest')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(354, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(354, {"canonical_name": "OTHER"})
    def test_cap_0355(self):
        r = tranche.run(355, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PARTIAL_EXTRACTION_INTERFACE')
        self.assertEqual(r["kind"], 'INTERFACE')
        self.assertEqual(r["binding"], 'partial_extraction_interface')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(355, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(355, {"canonical_name": "OTHER"})
    def test_cap_0356(self):
        r = tranche.run(356, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RANGE_FETCH_INTERFACE')
        self.assertEqual(r["kind"], 'INTERFACE')
        self.assertEqual(r["binding"], 'range_fetch_interface')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(356, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(356, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
