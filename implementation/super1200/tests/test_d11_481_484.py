#!/usr/bin/env python3
"""Negative tests for D11 481-484. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_481_484 as tranche


class D11Tranche481484Tests(unittest.TestCase):
    def test_cap_0481(self):
        r = tranche.run(481, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FAILED_PATTERN_REGISTRY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REGISTRY')
        self.assertEqual(r["binding"], 'failed_pattern_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(481, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(481, {"canonical_name": "OTHER"})
    def test_cap_0482(self):
        r = tranche.run(482, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ROOT_CAUSE_PATTERN_REGISTRY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REGISTRY')
        self.assertEqual(r["binding"], 'root_cause_pattern_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(482, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(482, {"canonical_name": "OTHER"})
    def test_cap_0483(self):
        r = tranche.run(483, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REPAIR_PATTERN_REGISTRY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REGISTRY')
        self.assertEqual(r["binding"], 'repair_pattern_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(483, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(483, {"canonical_name": "OTHER"})
    def test_cap_0484(self):
        r = tranche.run(484, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TIME_TO_RESOLUTION_LEDGER')
        self.assertEqual(r["kind"], 'METRIC_LEDGER')
        self.assertEqual(r["binding"], 'time_to_resolution_ledger')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(484, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(484, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
