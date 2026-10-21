#!/usr/bin/env python3
"""Negative tests for D07 295-298. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_295_298 as tranche


class D07Tranche295298Tests(unittest.TestCase):
    def test_cap_0295(self):
        r = tranche.run(295, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GROUNDED_THEORY_WORKFLOW')
        self.assertEqual(r["kind"], 'WORKFLOW')
        self.assertEqual(r["binding"], 'grounded_theory_workflow')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(295, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(295, {"canonical_name": "OTHER"})
    def test_cap_0296(self):
        r = tranche.run(296, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INTERCODER_RELIABILITY')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'intercoder_reliability')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(296, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(296, {"canonical_name": "OTHER"})
    def test_cap_0297(self):
        r = tranche.run(297, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AUDIT_TRAIL_QUALITATIVE')
        self.assertEqual(r["kind"], 'AUDIT_LEDGER')
        self.assertEqual(r["binding"], 'audit_trail_qualitative')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(297, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(297, {"canonical_name": "OTHER"})
    def test_cap_0298(self):
        r = tranche.run(298, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MEMOING_SYSTEM')
        self.assertEqual(r["kind"], 'KNOWLEDGE_STORE')
        self.assertEqual(r["binding"], 'memoing_system')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(298, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(298, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
