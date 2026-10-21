#!/usr/bin/env python3
"""Negative tests for D22 1149-1152. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1149_1152 as tranche


class D22Tranche11491152Tests(unittest.TestCase):
    def test_cap_1149(self):
        r = tranche.run(1149, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEFENSIVE_RULE_COMPILER')
        self.assertEqual(r["kind"], 'RULE_COMPILER')
        self.assertEqual(r["binding"], 'defensive_rule_compiler')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1149, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1149, {"canonical_name": "OTHER"})
    def test_cap_1150(self):
        r = tranche.run(1150, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PREVENTIVE_CONTROL_SYNTHESIS')
        self.assertEqual(r["kind"], 'PREVENTION_ENGINE')
        self.assertEqual(r["binding"], 'preventive_control_synthesis')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1150, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1150, {"canonical_name": "OTHER"})
    def test_cap_1151(self):
        r = tranche.run(1151, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_KNOWLEDGE_DEDUPLICATION')
        self.assertEqual(r["kind"], 'DATA_ENGINE')
        self.assertEqual(r["binding"], 'threat_knowledge_deduplication')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1151, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1151, {"canonical_name": "OTHER"})
    def test_cap_1152(self):
        r = tranche.run(1152, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_KNOWLEDGE_COMPRESSION')
        self.assertEqual(r["kind"], 'DATA_ENGINE')
        self.assertEqual(r["binding"], 'threat_knowledge_compression')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1152, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1152, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
