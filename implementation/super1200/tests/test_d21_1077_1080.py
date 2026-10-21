#!/usr/bin/env python3
"""Negative tests for D21 1077-1080. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d21_1077_1080 as tranche


class D21Tranche10771080Tests(unittest.TestCase):
    def test_cap_1077(self):
        r = tranche.run(1077, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_ROLLBACK')
        self.assertEqual(r["kind"], 'RECOVERY_ENGINE')
        self.assertEqual(r["binding"], 'substitute_rollback')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1077, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1077, {"canonical_name": "OTHER"})
    def test_cap_1078(self):
        r = tranche.run(1078, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_DEPENDENCY_RELEASE')
        self.assertEqual(r["kind"], 'CONTINUITY_ENGINE')
        self.assertEqual(r["binding"], 'quarantine_dependency_release')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1078, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1078, {"canonical_name": "OTHER"})
    def test_cap_1079(self):
        r = tranche.run(1079, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUBSTITUTE_LEARNING_ENGINE')
        self.assertEqual(r["kind"], 'KNOWLEDGE_ENGINE')
        self.assertEqual(r["binding"], 'substitute_learning_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1079, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1079, {"canonical_name": "OTHER"})
    def test_cap_1080(self):
        r = tranche.run(1080, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_CONTINUITY_GATE')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'security_continuity_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1080, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1080, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
