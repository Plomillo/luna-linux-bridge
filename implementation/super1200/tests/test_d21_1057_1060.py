#!/usr/bin/env python3
"""Negative tests for D21 1057-1060. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1057_1060 as tranche


class D21Tranche10571060Tests(unittest.TestCase):
    def test_cap_1057(self):
        r = tranche.run(1057, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_PROVENANCE')
        self.assertEqual(r["kind"], 'PROVENANCE_RECORD')
        self.assertEqual(r["binding"], 'substitute_provenance')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1057, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1057, {"canonical_name": "OTHER"})
    def test_cap_1058(self):
        r = tranche.run(1058, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_SBOM')
        self.assertEqual(r["kind"], 'SBOM_ARTIFACT')
        self.assertEqual(r["binding"], 'substitute_sbom')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1058, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1058, {"canonical_name": "OTHER"})
    def test_cap_1059(self):
        r = tranche.run(1059, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_REPRODUCIBLE_BUILD')
        self.assertEqual(r["kind"], 'BUILD_ASSURANCE')
        self.assertEqual(r["binding"], 'substitute_reproducible_build')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1059, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1059, {"canonical_name": "OTHER"})
    def test_cap_1060(self):
        r = tranche.run(1060, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_SECURITY_BASELINE')
        self.assertEqual(r["kind"], 'SECURITY_BASELINE')
        self.assertEqual(r["binding"], 'substitute_security_baseline')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1060, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1060, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
