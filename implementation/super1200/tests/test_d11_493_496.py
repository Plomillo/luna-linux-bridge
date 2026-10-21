#!/usr/bin/env python3
"""Negative tests for D11 493-496. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_493_496 as tranche


class D11Tranche493496Tests(unittest.TestCase):
    def test_cap_0493(self):
        r = tranche.run(493, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RUNBOOK_GENERATOR')
        self.assertEqual(r["kind"], 'FACTORY_TOOL')
        self.assertEqual(r["binding"], 'runbook_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(493, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(493, {"canonical_name": "OTHER"})
    def test_cap_0494(self):
        r = tranche.run(494, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RUNBOOK_VALIDATOR')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'runbook_validator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(494, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(494, {"canonical_name": "OTHER"})
    def test_cap_0495(self):
        r = tranche.run(495, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RUNBOOK_PROMOTION')
        self.assertEqual(r["kind"], 'PROMOTION_GATE')
        self.assertEqual(r["binding"], 'runbook_promotion')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(495, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(495, {"canonical_name": "OTHER"})
    def test_cap_0496(self):
        r = tranche.run(496, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AUTOMATION_OPPORTUNITY_DETECTOR')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'automation_opportunity_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(496, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(496, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
