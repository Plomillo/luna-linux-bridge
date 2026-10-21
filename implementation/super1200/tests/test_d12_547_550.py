#!/usr/bin/env python3
"""Negative tests for D12 547-550. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_547_550 as tranche


class D12Tranche547550Tests(unittest.TestCase):
    def test_cap_0547(self):
        r = tranche.run(547, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ADR_REGISTRY')
        self.assertEqual(r["kind"], 'DECISION_REGISTRY')
        self.assertEqual(r["binding"], 'adr_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(547, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(547, {"canonical_name": "OTHER"})
    def test_cap_0548(self):
        r = tranche.run(548, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DECISION_ID')
        self.assertEqual(r["kind"], 'IDENTITY_PRIMITIVE')
        self.assertEqual(r["binding"], 'decision_id')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(548, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(548, {"canonical_name": "OTHER"})
    def test_cap_0549(self):
        r = tranche.run(549, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DECISION_CONTEXT')
        self.assertEqual(r["kind"], 'DECISION_RECORD')
        self.assertEqual(r["binding"], 'decision_context')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(549, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(549, {"canonical_name": "OTHER"})
    def test_cap_0550(self):
        r = tranche.run(550, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ALTERNATIVES_CONSIDERED')
        self.assertEqual(r["kind"], 'DECISION_RECORD')
        self.assertEqual(r["binding"], 'alternatives_considered')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(550, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(550, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
