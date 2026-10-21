#!/usr/bin/env python3
"""Negative tests for D18 837-840. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d18_837_840 as tranche


class D18Tranche837840Tests(unittest.TestCase):
    def test_cap_0837(self):
        r = tranche.run(837, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_FREEZE_PROTECTION')
        self.assertEqual(r["kind"], 'SECURITY_ENGINE')
        self.assertEqual(r["binding"], 'update_freeze_protection')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(837, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(837, {"canonical_name": "OTHER"})
    def test_cap_0838(self):
        r = tranche.run(838, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_ROLLBACK_ATTACK_PROTECTION')
        self.assertEqual(r["kind"], 'SECURITY_ENGINE')
        self.assertEqual(r["binding"], 'update_rollback_attack_protection')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(838, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(838, {"canonical_name": "OTHER"})
    def test_cap_0839(self):
        r = tranche.run(839, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_PROVENANCE_GATE')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'update_provenance_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(839, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(839, {"canonical_name": "OTHER"})
    def test_cap_0840(self):
        r = tranche.run(840, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UPDATE_CERTIFICATION_GATE')
        self.assertEqual(r["kind"], 'ASSURANCE_GATE')
        self.assertEqual(r["binding"], 'update_certification_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(840, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(840, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
