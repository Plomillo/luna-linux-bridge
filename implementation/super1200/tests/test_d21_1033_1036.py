#!/usr/bin/env python3
"""Negative tests for D21 1033-1036. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1033_1036 as tranche


class D21Tranche10331036Tests(unittest.TestCase):
    def test_cap_1033(self):
        r = tranche.run(1033, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MULTI_ENGINE_RESCAN')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'multi_engine_rescan')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1033, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1033, {"canonical_name": "OTHER"})
    def test_cap_1034(self):
        r = tranche.run(1034, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FALSE_SANITIZATION_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'false_sanitization_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1034, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1034, {"canonical_name": "OTHER"})
    def test_cap_1035(self):
        r = tranche.run(1035, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INFORMATION_EXTRACTION_FALLBACK')
        self.assertEqual(r["kind"], 'RECOVERY_ENGINE')
        self.assertEqual(r["binding"], 'information_extraction_fallback')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1035, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1035, {"canonical_name": "OTHER"})
    def test_cap_1036(self):
        r = tranche.run(1036, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SAFE_FORMAT_TRANSCODER')
        self.assertEqual(r["kind"], 'FORMAT_ENGINE')
        self.assertEqual(r["binding"], 'safe_format_transcoder')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1036, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1036, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
