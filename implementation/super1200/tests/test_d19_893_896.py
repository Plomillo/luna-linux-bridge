#!/usr/bin/env python3
"""Negative tests for D19 893-896. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_893_896 as tranche


class D19Tranche893896Tests(unittest.TestCase):
    def test_cap_0893(self):
        r = tranche.run(893, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DOCUMENT_MALWARE_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'document_malware_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(893, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(893, {"canonical_name": "OTHER"})
    def test_cap_0894(self):
        r = tranche.run(894, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARCHIVE_MALWARE_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'archive_malware_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(894, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(894, {"canonical_name": "OTHER"})
    def test_cap_0895(self):
        r = tranche.run(895, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXECUTABLE_MALWARE_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'executable_malware_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(895, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(895, {"canonical_name": "OTHER"})
    def test_cap_0896(self):
        r = tranche.run(896, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MEMORY_MALWARE_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'memory_malware_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(896, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(896, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
