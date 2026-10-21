#!/usr/bin/env python3
"""Negative tests for D07 235-238. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_235_238 as d07


class D07Tranche235238Tests(unittest.TestCase):
    def test_cap_0235(self):
        r = d07.run(235, {"rounds": 2})
        self.assertEqual(r["canonical_name"], "DEBATE_ENGINE")
        self.assertFalse(r["certification_granted"])

    def test_cap_0236(self):
        r = d07.run(236, {})
        self.assertEqual(r["canonical_name"], "CRITIC_ENGINE")
        self.assertFalse(r["certification_granted"])

    def test_cap_0237(self):
        r = d07.run(237, {})
        self.assertEqual(r["canonical_name"], "JUDGE_ENGINE")
        self.assertFalse(r["certification_granted"])

    def test_cap_0238(self):
        r = d07.run(238, {})
        self.assertEqual(r["canonical_name"], "CONSENSUS_ENGINE")
        self.assertFalse(r["certification_granted"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
