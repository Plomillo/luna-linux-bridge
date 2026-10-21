#!/usr/bin/env python3
"""Negative tests for D21 1037-1040. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1037_1040 as tranche


class D21Tranche10371040Tests(unittest.TestCase):
    def test_cap_1037(self):
        r = tranche.run(1037, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'READ_ONLY_SAFE_VIEW')
        self.assertEqual(r["kind"], 'SAFE_VIEW_INTERFACE')
        self.assertEqual(r["binding"], 'read_only_safe_view')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1037, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1037, {"canonical_name": "OTHER"})
    def test_cap_1038(self):
        r = tranche.run(1038, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SANITIZATION_POLICY_ENGINE')
        self.assertEqual(r["kind"], 'POLICY_ENGINE')
        self.assertEqual(r["binding"], 'sanitization_policy_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1038, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1038, {"canonical_name": "OTHER"})
    def test_cap_1039(self):
        r = tranche.run(1039, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SANITIZER_SELF_TEST_CORPUS')
        self.assertEqual(r["kind"], 'TEST_DATASET')
        self.assertEqual(r["binding"], 'sanitizer_self_test_corpus')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1039, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1039, {"canonical_name": "OTHER"})
    def test_cap_1040(self):
        r = tranche.run(1040, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARTIFACT_RECOVERY_CERTIFICATION_GATE')
        self.assertEqual(r["kind"], 'ASSURANCE_GATE')
        self.assertEqual(r["binding"], 'artifact_recovery_certification_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1040, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1040, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
