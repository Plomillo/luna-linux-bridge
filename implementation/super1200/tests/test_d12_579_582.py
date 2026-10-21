#!/usr/bin/env python3
"""Negative tests for D12 579-582. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_579_582 as tranche


class D12Tranche579582Tests(unittest.TestCase):
    def test_cap_0579(self):
        r = tranche.run(579, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AUDITABILITY_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'auditability_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(579, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(579, {"canonical_name": "OTHER"})
    def test_cap_0580(self):
        r = tranche.run(580, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CERTIFIABILITY_SCORE')
        self.assertEqual(r["kind"], 'READINESS_METRIC')
        self.assertEqual(r["binding"], 'certifiability_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(580, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(580, {"canonical_name": "OTHER"})
    def test_cap_0581(self):
        r = tranche.run(581, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PORTABILITY_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'portability_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(581, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(581, {"canonical_name": "OTHER"})
    def test_cap_0582(self):
        r = tranche.run(582, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SELF_HOSTING_SCORE')
        self.assertEqual(r["kind"], 'METRIC_ENGINE')
        self.assertEqual(r["binding"], 'self_hosting_score')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(582, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(582, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
