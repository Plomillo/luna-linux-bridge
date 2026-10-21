#!/usr/bin/env python3
"""Negative tests for D14 657-660. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d14_657_660 as tranche


class D14Tranche657660Tests(unittest.TestCase):
    def test_cap_0657(self):
        r = tranche.run(657, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_CLOSURE_CRITERIA')
        self.assertEqual(r["kind"], 'POLICY/GATE')
        self.assertEqual(r["binding"], 'uncertainty_closure_criteria')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(657, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(657, {"canonical_name": "OTHER"})
    def test_cap_0658(self):
        r = tranche.run(658, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_REOPENING_ENGINE')
        self.assertEqual(r["kind"], 'STATE_ENGINE')
        self.assertEqual(r["binding"], 'uncertainty_reopening_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(658, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(658, {"canonical_name": "OTHER"})
    def test_cap_0659(self):
        r = tranche.run(659, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNKNOWN_ESCALATION_ENGINE')
        self.assertEqual(r["kind"], 'ESCALATION_ENGINE')
        self.assertEqual(r["binding"], 'unknown_escalation_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(659, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(659, {"canonical_name": "OTHER"})
    def test_cap_0660(self):
        r = tranche.run(660, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNCERTAINTY_KILL_RECEIPT')
        self.assertEqual(r["kind"], 'RECEIPT')
        self.assertEqual(r["binding"], 'uncertainty_kill_receipt')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(660, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(660, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
