#!/usr/bin/env python3
"""Negative tests for D13 638-640. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_638_640 as tranche


class D13Tranche638640Tests(unittest.TestCase):
    def test_cap_0638(self):
        r = tranche.run(638, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ACCESSIBILITY_ENGINE')
        self.assertEqual(r["kind"], 'QUALITY_ENGINE')
        self.assertEqual(r["binding"], 'accessibility_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(638, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(638, {"canonical_name": "OTHER"})
    def test_cap_0639(self):
        r = tranche.run(639, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MULTILINGUAL_PEDAGOGY_ENGINE')
        self.assertEqual(r["kind"], 'PEDAGOGY_ENGINE')
        self.assertEqual(r["binding"], 'multilingual_pedagogy_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(639, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(639, {"canonical_name": "OTHER"})
    def test_cap_0640(self):
        r = tranche.run(640, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PEDAGOGICAL_CERTIFICATION_GATE')
        self.assertEqual(r["kind"], 'CERTIFICATION_READINESS_GATE')
        self.assertEqual(r["binding"], 'pedagogical_certification_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(640, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(640, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
