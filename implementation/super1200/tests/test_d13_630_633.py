#!/usr/bin/env python3
"""Negative tests for D13 630-633. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_630_633 as tranche


class D13Tranche630633Tests(unittest.TestCase):
    def test_cap_0630(self):
        r = tranche.run(630, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROGRESSIVE_DISCLOSURE_ENGINE')
        self.assertEqual(r["kind"], 'PRESENTATION_ENGINE')
        self.assertEqual(r["binding"], 'progressive_disclosure_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(630, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(630, {"canonical_name": "OTHER"})
    def test_cap_0631(self):
        r = tranche.run(631, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPERTISE_LEVEL_ADAPTER')
        self.assertEqual(r["kind"], 'PRESENTATION_ADAPTER')
        self.assertEqual(r["binding"], 'expertise_level_adapter')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(631, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(631, {"canonical_name": "OTHER"})
    def test_cap_0632(self):
        r = tranche.run(632, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TEACH_BACK_ENGINE')
        self.assertEqual(r["kind"], 'ASSESSMENT_ENGINE')
        self.assertEqual(r["binding"], 'teach_back_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(632, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(632, {"canonical_name": "OTHER"})
    def test_cap_0633(self):
        r = tranche.run(633, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TRANSFER_ASSESSMENT_ENGINE')
        self.assertEqual(r["kind"], 'ASSESSMENT_ENGINE')
        self.assertEqual(r["binding"], 'transfer_assessment_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(633, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(633, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
