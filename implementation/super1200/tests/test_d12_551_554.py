#!/usr/bin/env python3
"""Negative tests for D12 551-554. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_551_554 as tranche


class D12Tranche551554Tests(unittest.TestCase):
    def test_cap_0551(self):
        r = tranche.run(551, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DECISION_EVIDENCE')
        self.assertEqual(r["kind"], 'TRACEABILITY_ENGINE')
        self.assertEqual(r["binding"], 'decision_evidence')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(551, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(551, {"canonical_name": "OTHER"})
    def test_cap_0552(self):
        r = tranche.run(552, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DECISION_REVERSIBILITY')
        self.assertEqual(r["kind"], 'RISK_ANALYZER')
        self.assertEqual(r["binding"], 'decision_reversibility')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(552, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(552, {"canonical_name": "OTHER"})
    def test_cap_0553(self):
        r = tranche.run(553, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DECISION_EXPIRATION')
        self.assertEqual(r["kind"], 'POLICY')
        self.assertEqual(r["binding"], 'decision_expiration')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(553, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(553, {"canonical_name": "OTHER"})
    def test_cap_0554(self):
        r = tranche.run(554, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DECISION_SUPERSESSION')
        self.assertEqual(r["kind"], 'RELATION_ENGINE')
        self.assertEqual(r["binding"], 'decision_supersession')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(554, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(554, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
