#!/usr/bin/env python3
"""Negative tests for D20 993-996. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d20_993_996 as tranche


class D20Tranche993996Tests(unittest.TestCase):
    def test_cap_0993(self):
        r = tranche.run(993, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPROMISE_RECOVERY_ENGINE')
        self.assertEqual(r["kind"], 'RECOVERY_ENGINE')
        self.assertEqual(r["binding"], 'compromise_recovery_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(993, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(993, {"canonical_name": "OTHER"})
    def test_cap_0994(self):
        r = tranche.run(994, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'POST_ERADICATION_VERIFICATION')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'post_eradication_verification')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(994, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(994, {"canonical_name": "OTHER"})
    def test_cap_0995(self):
        r = tranche.run(995, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'REINFECTION_PREVENTION_ENGINE')
        self.assertEqual(r["kind"], 'PREVENTION_ENGINE')
        self.assertEqual(r["binding"], 'reinfection_prevention_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(995, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(995, {"canonical_name": "OTHER"})
    def test_cap_0996(self):
        r = tranche.run(996, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INCIDENT_KNOWLEDGE_COMPILER')
        self.assertEqual(r["kind"], 'KNOWLEDGE_ENGINE')
        self.assertEqual(r["binding"], 'incident_knowledge_compiler')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(996, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(996, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
