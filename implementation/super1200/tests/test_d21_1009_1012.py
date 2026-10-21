#!/usr/bin/env python3
"""Negative tests for D21 1009-1012. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1009_1012 as tranche


class D21Tranche10091012Tests(unittest.TestCase):
    def test_cap_1009(self):
        r = tranche.run(1009, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONTENT_DISARM_RECONSTRUCTION')
        self.assertEqual(r["kind"], 'SANITIZATION_ENGINE')
        self.assertEqual(r["binding"], 'content_disarm_reconstruction')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1009, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1009, {"canonical_name": "OTHER"})
    def test_cap_1010(self):
        r = tranche.run(1010, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FORMAT_AWARE_SANITIZER')
        self.assertEqual(r["kind"], 'SANITIZATION_ORCHESTRATOR')
        self.assertEqual(r["binding"], 'format_aware_sanitizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1010, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1010, {"canonical_name": "OTHER"})
    def test_cap_1011(self):
        r = tranche.run(1011, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PDF_SANITIZER')
        self.assertEqual(r["kind"], 'FORMAT_ENGINE')
        self.assertEqual(r["binding"], 'pdf_sanitizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1011, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1011, {"canonical_name": "OTHER"})
    def test_cap_1012(self):
        r = tranche.run(1012, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OFFICE_DOCUMENT_SANITIZER')
        self.assertEqual(r["kind"], 'FORMAT_ENGINE')
        self.assertEqual(r["binding"], 'office_document_sanitizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1012, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1012, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
