#!/usr/bin/env python3
"""Negative tests for D21 1021-1024. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1021_1024 as tranche


class D21Tranche10211024Tests(unittest.TestCase):
    def test_cap_1021(self):
        r = tranche.run(1021, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TRUSTED_REBUILD_PREFERENCE')
        self.assertEqual(r["kind"], 'SECURITY_POLICY')
        self.assertEqual(r["binding"], 'trusted_rebuild_preference')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1021, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1021, {"canonical_name": "OTHER"})
    def test_cap_1022(self):
        r = tranche.run(1022, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'KNOWN_GOOD_COMPONENT_SUBSTITUTION')
        self.assertEqual(r["kind"], 'RECOVERY_PATTERN')
        self.assertEqual(r["binding"], 'known_good_component_substitution')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1022, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1022, {"canonical_name": "OTHER"})
    def test_cap_1023(self):
        r = tranche.run(1023, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SEMANTIC_PRESERVATION_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'semantic_preservation_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1023, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1023, {"canonical_name": "OTHER"})
    def test_cap_1024(self):
        r = tranche.run(1024, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FUNCTIONAL_PRESERVATION_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'functional_preservation_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1024, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1024, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
