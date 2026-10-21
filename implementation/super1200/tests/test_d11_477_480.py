#!/usr/bin/env python3
"""Negative tests for D11 477-480. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_477_480 as tranche


class D11Tranche477480Tests(unittest.TestCase):
    def test_cap_0477(self):
        r = tranche.run(477, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXPERIENCE_LEDGER')
        self.assertEqual(r["kind"], 'LEDGER')
        self.assertEqual(r["binding"], 'experience_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(477, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(477, {"canonical_name": "OTHER"})
    def test_cap_0478(self):
        r = tranche.run(478, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MISSION_HISTORY')
        self.assertEqual(r["kind"], 'LEDGER_VIEW')
        self.assertEqual(r["binding"], 'mission_history')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(478, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(478, {"canonical_name": "OTHER"})
    def test_cap_0479(self):
        r = tranche.run(479, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MISSION_CLASSIFIER')
        self.assertEqual(r["kind"], 'CLASSIFIER')
        self.assertEqual(r["binding"], 'mission_classifier')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(479, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(479, {"canonical_name": "OTHER"})
    def test_cap_0480(self):
        r = tranche.run(480, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOLUTION_PATTERN_REGISTRY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REGISTRY')
        self.assertEqual(r["binding"], 'solution_pattern_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(480, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(480, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
