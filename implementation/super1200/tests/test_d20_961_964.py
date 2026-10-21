#!/usr/bin/env python3
"""Negative tests for D20 961-964. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d20_961_964 as tranche


class D20Tranche961964Tests(unittest.TestCase):
    def test_cap_0961(self):
        r = tranche.run(961, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SUSPICIOUS_OBJECT_INTAKE')
        self.assertEqual(r["kind"], 'SECURITY_WORKFLOW')
        self.assertEqual(r["binding"], 'suspicious_object_intake')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(961, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(961, {"canonical_name": "OTHER"})
    def test_cap_0962(self):
        r = tranche.run(962, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AUTOMATIC_CONTAINMENT_GATE')
        self.assertEqual(r["kind"], 'SECURITY_GATE')
        self.assertEqual(r["binding"], 'automatic_containment_gate')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(962, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(962, {"canonical_name": "OTHER"})
    def test_cap_0963(self):
        r = tranche.run(963, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_FABRIC')
        self.assertEqual(r["kind"], 'SECURITY_FABRIC')
        self.assertEqual(r["binding"], 'quarantine_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(963, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(963, {"canonical_name": "OTHER"})
    def test_cap_0964(self):
        r = tranche.run(964, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONTENT_ADDRESSED_QUARANTINE')
        self.assertEqual(r["kind"], 'STORE')
        self.assertEqual(r["binding"], 'content_addressed_quarantine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(964, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(964, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
