#!/usr/bin/env python3
"""Negative tests for D21 1013-1016. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1013_1016 as tranche


class D21Tranche10131016Tests(unittest.TestCase):
    def test_cap_1013(self):
        r = tranche.run(1013, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MACRO_ISOLATION_ENGINE')
        self.assertEqual(r["kind"], 'SANITIZATION_ENGINE')
        self.assertEqual(r["binding"], 'macro_isolation_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1013, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1013, {"canonical_name": "OTHER"})
    def test_cap_1014(self):
        r = tranche.run(1014, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EMBEDDED_OBJECT_SANITIZER')
        self.assertEqual(r["kind"], 'FORMAT_ENGINE')
        self.assertEqual(r["binding"], 'embedded_object_sanitizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1014, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1014, {"canonical_name": "OTHER"})
    def test_cap_1015(self):
        r = tranche.run(1015, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARCHIVE_COMPONENT_SANITIZER')
        self.assertEqual(r["kind"], 'FORMAT_ENGINE')
        self.assertEqual(r["binding"], 'archive_component_sanitizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1015, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1015, {"canonical_name": "OTHER"})
    def test_cap_1016(self):
        r = tranche.run(1016, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EMAIL_ATTACHMENT_SANITIZER')
        self.assertEqual(r["kind"], 'FORMAT_ENGINE')
        self.assertEqual(r["binding"], 'email_attachment_sanitizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1016, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1016, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
