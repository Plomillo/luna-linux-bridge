#!/usr/bin/env python3
"""Negative tests for D19 909-912. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_909_912 as tranche


class D19Tranche909912Tests(unittest.TestCase):
    def test_cap_0909(self):
        r = tranche.run(909, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PATCH_AVAILABILITY_ENGINE')
        self.assertEqual(r["kind"], 'RESEARCH_ENGINE')
        self.assertEqual(r["binding"], 'patch_availability_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(909, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(909, {"canonical_name": "OTHER"})
    def test_cap_0910(self):
        r = tranche.run(910, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_PATCH_PLANNER')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'security_patch_planner')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(910, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(910, {"canonical_name": "OTHER"})
    def test_cap_0911(self):
        r = tranche.run(911, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_CONFIGURATION_ANALYZER')
        self.assertEqual(r["kind"], 'SECURITY_ANALYZER')
        self.assertEqual(r["binding"], 'security_configuration_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(911, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(911, {"canonical_name": "OTHER"})
    def test_cap_0912(self):
        r = tranche.run(912, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECRET_EXPOSURE_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'secret_exposure_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(912, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(912, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
