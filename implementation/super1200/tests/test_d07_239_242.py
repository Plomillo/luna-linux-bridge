#!/usr/bin/env python3
"""Negative tests for D07 239-242. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_239_242 as d07

class D07Tranche239242Tests(unittest.TestCase):
    def test_cap_0239(self):
        r = d07.run(239, {"domain": "math"})
        self.assertEqual(r["canonical_name"], "SPECIALIST_ROUTING")
        self.assertFalse(r["certification_granted"])

    def test_cap_0240(self):
        r = d07.run(240, {"stages": ["a", "b"]})
        self.assertEqual(r["canonical_name"], "MODEL_CASCADE")
        self.assertFalse(r["certification_granted"])

    def test_cap_0241(self):
        r = d07.run(241, {})
        self.assertEqual(r["canonical_name"], "CONFIDENCE_ROUTING")
        self.assertFalse(r["certification_granted"])

    def test_cap_0242(self):
        r = d07.run(242, {"budget": 10})
        self.assertEqual(r["canonical_name"], "COST_AWARE_ROUTING")
        self.assertFalse(r["certification_granted"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
