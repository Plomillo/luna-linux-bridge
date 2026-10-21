#!/usr/bin/env python3
"""Negative tests for D12 571-574. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_571_574 as tranche


class D12Tranche571574Tests(unittest.TestCase):
    def test_cap_0571(self):
        r = tranche.run(571, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OPENSSF_SCORECARD_ADAPTER')
        self.assertEqual(r["kind"], 'EXT_SERVICE_TOOL_ADAPTER')
        self.assertEqual(r["binding"], 'openssf_scorecard_adapter')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(571, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(571, {"canonical_name": "OTHER"})
    def test_cap_0572(self):
        r = tranche.run(572, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BEST_PRACTICES_SELF_AUDIT')
        self.assertEqual(r["kind"], 'AUDIT_ENGINE')
        self.assertEqual(r["binding"], 'best_practices_self_audit')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(572, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(572, {"canonical_name": "OTHER"})
    def test_cap_0573(self):
        r = tranche.run(573, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REPOSITORY_HEALTH_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'repository_health_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(573, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(573, {"canonical_name": "OTHER"})
    def test_cap_0574(self):
        r = tranche.run(574, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MAINTAINABILITY_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'maintainability_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(574, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(574, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
