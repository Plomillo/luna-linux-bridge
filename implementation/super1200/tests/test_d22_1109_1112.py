#!/usr/bin/env python3
"""Negative tests for D22 1109-1112. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1109_1112 as tranche


class D22Tranche11091112Tests(unittest.TestCase):
    def test_cap_1109(self):
        r = tranche.run(1109, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_KNOWLEDGE_PRESERVATION_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'threat_knowledge_preservation_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1109, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1109, {"canonical_name": "OTHER"})
    def test_cap_1110(self):
        r = tranche.run(1110, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'NON_EXECUTABLE_THREAT_ARCHIVE')
        self.assertEqual(r["kind"], 'KNOWLEDGE_STORE')
        self.assertEqual(r["binding"], 'non_executable_threat_archive')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1110, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1110, {"canonical_name": "OTHER"})
    def test_cap_1111(self):
        r = tranche.run(1111, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXTERNAL_REFERENCE_ADAPTER')
        self.assertEqual(r["kind"], 'INTELLIGENCE_ADAPTER')
        self.assertEqual(r["binding"], 'external_reference_adapter')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1111, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1111, {"canonical_name": "OTHER"})
    def test_cap_1112(self):
        r = tranche.run(1112, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_REACQUISITION_POLICY')
        self.assertEqual(r["kind"], 'POLICY')
        self.assertEqual(r["binding"], 'threat_reacquisition_policy')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1112, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1112, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
