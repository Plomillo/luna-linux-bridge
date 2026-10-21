#!/usr/bin/env python3
"""Negative tests for D11 485-488. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_485_488 as tranche


class D11Tranche485488Tests(unittest.TestCase):
    def test_cap_0485(self):
        r = tranche.run(485, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RETRY_COST_LEDGER')
        self.assertEqual(r["kind"], 'METRIC_LEDGER')
        self.assertEqual(r["binding"], 'retry_cost_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(485, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(485, {"canonical_name": "OTHER"})
    def test_cap_0486(self):
        r = tranche.run(486, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RESEARCH_COST_LEDGER')
        self.assertEqual(r["kind"], 'METRIC_LEDGER')
        self.assertEqual(r["binding"], 'research_cost_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(486, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(486, {"canonical_name": "OTHER"})
    def test_cap_0487(self):
        r = tranche.run(487, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'VALIDATION_COST_LEDGER')
        self.assertEqual(r["kind"], 'METRIC_LEDGER')
        self.assertEqual(r["binding"], 'validation_cost_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(487, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(487, {"canonical_name": "OTHER"})
    def test_cap_0488(self):
        r = tranche.run(488, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CERTIFICATION_COST_LEDGER')
        self.assertEqual(r["kind"], 'METRIC_LEDGER')
        self.assertEqual(r["binding"], 'certification_cost_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(488, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(488, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
