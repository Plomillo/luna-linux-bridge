#!/usr/bin/env python3
"""Negative tests for D22 1133-1136. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1133_1136 as tranche


class D22Tranche11331136Tests(unittest.TestCase):
    def test_cap_1133(self):
        r = tranche.run(1133, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BEHAVIORAL_INDICATOR_REGISTRY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REGISTRY')
        self.assertEqual(r["binding"], 'behavioral_indicator_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1133, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1133, {"canonical_name": "OTHER"})
    def test_cap_1134(self):
        r = tranche.run(1134, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PERSISTENCE_TECHNIQUE_REGISTRY')
        self.assertEqual(r["kind"], 'KNOWLEDGE_REGISTRY')
        self.assertEqual(r["binding"], 'persistence_technique_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1134, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1134, {"canonical_name": "OTHER"})
    def test_cap_1135(self):
        r = tranche.run(1135, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INITIAL_ACCESS_KB')
        self.assertEqual(r["kind"], 'KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'initial_access_kb')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1135, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1135, {"canonical_name": "OTHER"})
    def test_cap_1136(self):
        r = tranche.run(1136, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PRIVILEGE_ESCALATION_KB')
        self.assertEqual(r["kind"], 'KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'privilege_escalation_kb')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1136, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1136, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
