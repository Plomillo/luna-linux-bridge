#!/usr/bin/env python3
"""Negative tests for D07 243-246. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_243_246 as tranche


class D07Tranche243246Tests(unittest.TestCase):
    def test_cap_0243(self):
        r = tranche.run(243, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CAPABILITY_AWARE_ROUTING')
        self.assertEqual(r["kind"], 'ROUTING_ENGINE')
        self.assertEqual(r["binding"], 'capability_aware_routing')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(243, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(243, {"canonical_name": "OTHER"})
    def test_cap_0244(self):
        r = tranche.run(244, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FAILURE_AWARE_ROUTING')
        self.assertEqual(r["kind"], 'ROUTING_ENGINE')
        self.assertEqual(r["binding"], 'failure_aware_routing')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(244, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(244, {"canonical_name": "OTHER"})
    def test_cap_0245(self):
        r = tranche.run(245, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REDUNDANT_REASONING')
        self.assertEqual(r["kind"], 'REASONING_PATTERN')
        self.assertEqual(r["binding"], 'redundant_reasoning')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(245, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(245, {"canonical_name": "OTHER"})
    def test_cap_0246(self):
        r = tranche.run(246, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DIVERSITY_ENFORCEMENT')
        self.assertEqual(r["kind"], 'INDEPENDENCE_ENGINE')
        self.assertEqual(r["binding"], 'diversity_enforcement')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(246, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(246, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
