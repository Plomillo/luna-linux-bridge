#!/usr/bin/env python3
"""Negative tests for D08 345-348. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_345_348 as tranche


class D08Tranche345348Tests(unittest.TestCase):
    def test_cap_0345(self):
        r = tranche.run(345, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TEXT_CORPUS_COMPRESSION')
        self.assertEqual(r["kind"], 'DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'text_corpus_compression')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(345, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(345, {"canonical_name": "OTHER"})
    def test_cap_0346(self):
        r = tranche.run(346, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOURCE_TREE_COMPRESSION')
        self.assertEqual(r["kind"], 'DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'source_tree_compression')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(346, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(346, {"canonical_name": "OTHER"})
    def test_cap_0347(self):
        r = tranche.run(347, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BINARY_COMPRESSION')
        self.assertEqual(r["kind"], 'DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'binary_compression')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(347, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(347, {"canonical_name": "OTHER"})
    def test_cap_0348(self):
        r = tranche.run(348, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOLID_ARCHIVE_ENGINE')
        self.assertEqual(r["kind"], 'ARCHIVE_ENGINE')
        self.assertEqual(r["binding"], 'solid_archive_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(348, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(348, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
