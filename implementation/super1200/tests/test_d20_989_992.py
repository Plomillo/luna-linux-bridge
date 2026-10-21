#!/usr/bin/env python3
"""Negative tests for D20 989-992. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d20_989_992 as tranche


class D20Tranche989992Tests(unittest.TestCase):
    def test_cap_0989(self):
        r = tranche.run(989, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INITIAL_ACCESS_ANALYZER')
        self.assertEqual(r["kind"], 'FORENSIC_ANALYZER')
        self.assertEqual(r["binding"], 'initial_access_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(989, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(989, {"canonical_name": "OTHER"})
    def test_cap_0990(self):
        r = tranche.run(990, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ROOT_CAUSE_SECURITY_ANALYZER')
        self.assertEqual(r["kind"], 'INCIDENT_ANALYZER')
        self.assertEqual(r["binding"], 'root_cause_security_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(990, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(990, {"canonical_name": "OTHER"})
    def test_cap_0991(self):
        r = tranche.run(991, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_ERADICATION_ENGINE')
        self.assertEqual(r["kind"], 'REMEDIATION_ENGINE')
        self.assertEqual(r["binding"], 'malware_eradication_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(991, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(991, {"canonical_name": "OTHER"})
    def test_cap_0992(self):
        r = tranche.run(992, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PERSISTENCE_ERADICATION_ENGINE')
        self.assertEqual(r["kind"], 'REMEDIATION_ENGINE')
        self.assertEqual(r["binding"], 'persistence_eradication_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(992, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(992, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
