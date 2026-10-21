#!/usr/bin/env python3
"""Negative tests for D19 877-880. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_877_880 as tranche


class D19Tranche877880Tests(unittest.TestCase):
    def test_cap_0877(self):
        r = tranche.run(877, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FALSE_NEGATIVE_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'false_negative_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(877, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(877, {"canonical_name": "OTHER"})
    def test_cap_0878(self):
        r = tranche.run(878, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_REGRESSION_ENGINE')
        self.assertEqual(r["kind"], 'REGRESSION_ENGINE')
        self.assertEqual(r["binding"], 'security_regression_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(878, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(878, {"canonical_name": "OTHER"})
    def test_cap_0879(self):
        r = tranche.run(879, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_SELF_CRITIC')
        self.assertEqual(r["kind"], 'METACOGNITIVE_ENGINE')
        self.assertEqual(r["binding"], 'security_self_critic')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(879, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(879, {"canonical_name": "OTHER"})
    def test_cap_0880(self):
        r = tranche.run(880, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_NON_SELF_CERTIFICATION')
        self.assertEqual(r["kind"], 'GOVERNANCE_GATE')
        self.assertEqual(r["binding"], 'security_non_self_certification')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(880, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(880, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
