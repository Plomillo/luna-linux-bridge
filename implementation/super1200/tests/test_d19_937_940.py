#!/usr/bin/env python3
"""Negative tests for D19 937-940. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_937_940 as tranche


class D19Tranche937940Tests(unittest.TestCase):
    def test_cap_0937(self):
        r = tranche.run(937, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'WORKFLOW_SECURITY_ANALYZER')
        self.assertEqual(r["kind"], 'SECURITY_ANALYZER')
        self.assertEqual(r["binding"], 'workflow_security_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(937, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(937, {"canonical_name": "OTHER"})
    def test_cap_0938(self):
        r = tranche.run(938, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BRANCH_PROTECTION_AUDITOR')
        self.assertEqual(r["kind"], 'AUDITOR')
        self.assertEqual(r["binding"], 'branch_protection_auditor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(938, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(938, {"canonical_name": "OTHER"})
    def test_cap_0939(self):
        r = tranche.run(939, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REPOSITORY_TAMPER_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'repository_tamper_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(939, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(939, {"canonical_name": "OTHER"})
    def test_cap_0940(self):
        r = tranche.run(940, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CANONICAL_ARTIFACT_SECURITY_GUARD')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'canonical_artifact_security_guard')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(940, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(940, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
