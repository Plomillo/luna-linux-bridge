#!/usr/bin/env python3
"""Negative tests for D08 337-340. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_337_340 as tranche


class D08Tranche337340Tests(unittest.TestCase):
    def test_cap_0337(self):
        r = tranche.run(337, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LZ4_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_LIBRARY_TOOL')
        self.assertEqual(r["binding"], 'lz4_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(337, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(337, {"canonical_name": "OTHER"})
    def test_cap_0338(self):
        r = tranche.run(338, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'XZ_LZMA_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_BINARY_LIBRARY')
        self.assertEqual(r["binding"], 'xz_lzma_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(338, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(338, {"canonical_name": "OTHER"})
    def test_cap_0339(self):
        r = tranche.run(339, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BROTLI_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_LIBRARY_TOOL')
        self.assertEqual(r["binding"], 'brotli_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(339, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(339, {"canonical_name": "OTHER"})
    def test_cap_0340(self):
        r = tranche.run(340, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SEVEN_ZIP_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_BINARY_TOOL')
        self.assertEqual(r["binding"], 'seven_zip_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(340, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(340, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
