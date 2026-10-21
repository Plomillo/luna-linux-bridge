#!/usr/bin/env python3
"""Negative tests for D20 985-988. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d20_985_988 as tranche


class D20Tranche985988Tests(unittest.TestCase):
    def test_cap_0985(self):
        r = tranche.run(985, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FALSE_POSITIVE_LEARNING')
        self.assertEqual(r["kind"], 'LEARNING_ENGINE')
        self.assertEqual(r["binding"], 'false_positive_learning')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(985, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(985, {"canonical_name": "OTHER"})
    def test_cap_0986(self):
        r = tranche.run(986, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_CONFIRMATION_GATE')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'malware_confirmation_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(986, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(986, {"canonical_name": "OTHER"})
    def test_cap_0987(self):
        r = tranche.run(987, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INCIDENT_SCOPE_ENGINE')
        self.assertEqual(r["kind"], 'INCIDENT_ANALYZER')
        self.assertEqual(r["binding"], 'incident_scope_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(987, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(987, {"canonical_name": "OTHER"})
    def test_cap_0988(self):
        r = tranche.run(988, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PATIENT_ZERO_ANALYZER')
        self.assertEqual(r["kind"], 'FORENSIC_ANALYZER')
        self.assertEqual(r["binding"], 'patient_zero_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(988, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(988, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
