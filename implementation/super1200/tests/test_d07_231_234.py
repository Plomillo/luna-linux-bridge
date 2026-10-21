#!/usr/bin/env python3
"""Negative tests for D07 231-234. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_231_234 as d07

class D07FirstTrancheTests(unittest.TestCase):
    def test_cap_0231(self):
        r = d07.run(231, {"models": ["a", "b"]})
        self.assertEqual(r["canonical_name"], "MULTI_AI_ARCHITECTURE_FACTORY")
        self.assertFalse(r["certification_granted"])
        bad = d07.run(231, None)
        self.assertIn("error", bad)

    def test_cap_0232(self):
        r = d07.run(232, {"nodes": [1, 2]})
        self.assertEqual(r["canonical_name"], "AGENT_GRAPH_FACTORY")
        self.assertFalse(r["certification_granted"])

    def test_cap_0233(self):
        r = d07.run(233, {"routes": ["x"]})
        self.assertEqual(r["canonical_name"], "ROUTER_FACTORY")
        self.assertFalse(r["certification_granted"])

    def test_cap_0234(self):
        r = d07.run(234, {"members": ["m1"]})
        self.assertEqual(r["canonical_name"], "ENSEMBLE_ENGINE")
        self.assertFalse(r["certification_granted"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
