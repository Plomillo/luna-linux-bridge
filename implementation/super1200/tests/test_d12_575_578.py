#!/usr/bin/env python3
"""Negative tests for D12 575-578. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_575_578 as tranche


class D12Tranche575578Tests(unittest.TestCase):
    def test_cap_0575(self):
        r = tranche.run(575, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEPENDENCY_RISK_SCORE')
        self.assertEqual(r["kind"], 'RISK_ENGINE')
        self.assertEqual(r["binding"], 'dependency_risk_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(575, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(575, {"canonical_name": "OTHER"})
    def test_cap_0576(self):
        r = tranche.run(576, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_POSTURE_SCORE')
        self.assertEqual(r["kind"], 'RISK_METRIC')
        self.assertEqual(r["binding"], 'security_posture_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(576, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(576, {"canonical_name": "OTHER"})
    def test_cap_0577(self):
        r = tranche.run(577, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REPRODUCIBILITY_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'reproducibility_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(577, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(577, {"canonical_name": "OTHER"})
    def test_cap_0578(self):
        r = tranche.run(578, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TRACEABILITY_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'traceability_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(578, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(578, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
