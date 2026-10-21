#!/usr/bin/env python3
"""Negative tests for D22 1105-1108. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1105_1108 as tranche


class D22Tranche11051108Tests(unittest.TestCase):
    def test_cap_1105(self):
        r = tranche.run(1105, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DESTRUCTION_RECEIPT')
        self.assertEqual(r["kind"], 'RECEIPT')
        self.assertEqual(r["binding"], 'destruction_receipt')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1105, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1105, {"canonical_name": "OTHER"})
    def test_cap_1106(self):
        r = tranche.run(1106, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'POST_DESTRUCTION_VERIFICATION')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'post_destruction_verification')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1106, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1106, {"canonical_name": "OTHER"})
    def test_cap_1107(self):
        r = tranche.run(1107, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RESIDUAL_ARTIFACT_SCANNER')
        self.assertEqual(r["kind"], 'DEFENSIVE_SCANNER')
        self.assertEqual(r["binding"], 'residual_artifact_scanner')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1107, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1107, {"canonical_name": "OTHER"})
    def test_cap_1108(self):
        r = tranche.run(1108, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REINFECTION_VECTOR_CHECK')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'reinfection_vector_check')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1108, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1108, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
