#!/usr/bin/env python3
"""Negative tests for D19 861-864. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_861_864 as tranche


class D19Tranche861864Tests(unittest.TestCase):
    def test_cap_0861(self):
        r = tranche.run(861, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_METACOGNITIVE_DEFENSE_FABRIC')
        self.assertEqual(r["kind"], 'SECURITY_FABRIC')
        self.assertEqual(r["binding"], 'security_metacognitive_defense_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(861, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(861, {"canonical_name": "OTHER"})
    def test_cap_0862(self):
        r = tranche.run(862, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_ADVISER_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'security_adviser_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(862, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(862, {"canonical_name": "OTHER"})
    def test_cap_0863(self):
        r = tranche.run(863, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DOMAIN_SECURITY_ADVISER')
        self.assertEqual(r["kind"], 'SECURITY_COMPONENT_INTERFACE')
        self.assertEqual(r["binding"], 'domain_security_adviser')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(863, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(863, {"canonical_name": "OTHER"})
    def test_cap_0864(self):
        r = tranche.run(864, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SECURITY_OBSERVER')
        self.assertEqual(r["kind"], 'SECURITY_ROLE')
        self.assertEqual(r["binding"], 'security_observer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(864, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(864, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
