#!/usr/bin/env python3
"""Negative tests for D22 1165-1168. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1165_1168 as tranche


class D22Tranche11651168Tests(unittest.TestCase):
    def test_cap_1165(self):
        r = tranche.run(1165, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANTHROPOLOGY_OF_HARM_ENGINE')
        self.assertEqual(r["kind"], 'INTERPRETIVE_DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'anthropology_of_harm_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1165, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1165, {"canonical_name": "OTHER"})
    def test_cap_1166(self):
        r = tranche.run(1166, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MORAL_PSYCHOLOGY_ADAPTER')
        self.assertEqual(r["kind"], 'DISCIPLINE_ADAPTER')
        self.assertEqual(r["binding"], 'moral_psychology_adapter')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1166, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1166, {"canonical_name": "OTHER"})
    def test_cap_1167(self):
        r = tranche.run(1167, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CRIMINOLOGY_ADAPTER')
        self.assertEqual(r["kind"], 'DISCIPLINE_ADAPTER')
        self.assertEqual(r["binding"], 'criminology_adapter')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1167, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1167, {"canonical_name": "OTHER"})
    def test_cap_1168(self):
        r = tranche.run(1168, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOCIOLOGY_OF_CYBERCRIME')
        self.assertEqual(r["kind"], 'INTERDISCIPLINARY_DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'sociology_of_cybercrime')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1168, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1168, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
