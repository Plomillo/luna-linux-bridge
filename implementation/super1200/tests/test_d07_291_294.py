#!/usr/bin/env python3
"""Negative tests for D07 291-294. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_291_294 as tranche


class D07Tranche291294Tests(unittest.TestCase):
    def test_cap_0291(self):
        r = tranche.run(291, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THEMATIC_ANALYSIS')
        self.assertEqual(r["kind"], 'QUALITATIVE_ENGINE')
        self.assertEqual(r["binding"], 'thematic_analysis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(291, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(291, {"canonical_name": "OTHER"})
    def test_cap_0292(self):
        r = tranche.run(292, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONTENT_ANALYSIS')
        self.assertEqual(r["kind"], 'QUALITATIVE_ENGINE')
        self.assertEqual(r["binding"], 'content_analysis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(292, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(292, {"canonical_name": "OTHER"})
    def test_cap_0293(self):
        r = tranche.run(293, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DISCOURSE_ANALYSIS')
        self.assertEqual(r["kind"], 'QUALITATIVE_ENGINE')
        self.assertEqual(r["binding"], 'discourse_analysis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(293, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(293, {"canonical_name": "OTHER"})
    def test_cap_0294(self):
        r = tranche.run(294, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NARRATIVE_ANALYSIS')
        self.assertEqual(r["kind"], 'QUALITATIVE_ENGINE')
        self.assertEqual(r["binding"], 'narrative_analysis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(294, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(294, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
