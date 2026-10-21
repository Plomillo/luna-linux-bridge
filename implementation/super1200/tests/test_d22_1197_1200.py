#!/usr/bin/env python3
"""Negative tests for D22 1197-1200. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1197_1200 as tranche


class D22Tranche11971200Tests(unittest.TestCase):
    def test_cap_1197(self):
        r = tranche.run(1197, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HUMAN_THREAT_KNOWLEDGE_PROVENANCE')
        self.assertEqual(r["kind"], 'PROVENANCE_ENGINE')
        self.assertEqual(r["binding"], 'human_threat_knowledge_provenance')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1197, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1197, {"canonical_name": "OTHER"})
    def test_cap_1198(self):
        r = tranche.run(1198, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INTERDISCIPLINARY_THREAT_SYNTHESIS')
        self.assertEqual(r["kind"], 'DEFENSIVE_SYNTHESIS_ENGINE')
        self.assertEqual(r["binding"], 'interdisciplinary_threat_synthesis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1198, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1198, {"canonical_name": "OTHER"})
    def test_cap_1199(self):
        r = tranche.run(1199, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EVIL_TO_CYBER_HERMENEUTIC_BOUNDARY')
        self.assertEqual(r["kind"], 'EPISTEMIC_GOVERNANCE_BOUNDARY')
        self.assertEqual(r["binding"], 'evil_to_cyber_hermeneutic_boundary')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1199, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1199, {"canonical_name": "OTHER"})
    def test_cap_1200(self):
        r = tranche.run(1200, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREINFECTION_PREVENTION_GATE')
        self.assertEqual(r["kind"], 'GLOBAL_PREINFECTION_SECURITY_GATE')
        self.assertEqual(r["binding"], 'preinfection_prevention_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1200, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1200, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
