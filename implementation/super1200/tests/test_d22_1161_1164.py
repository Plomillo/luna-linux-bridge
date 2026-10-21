#!/usr/bin/env python3
"""Negative tests for D22 1161-1164. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1161_1164 as tranche


class D22Tranche11611164Tests(unittest.TestCase):
    def test_cap_1161(self):
        r = tranche.run(1161, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HUMAN_ORIGIN_THREAT_FABRIC')
        self.assertEqual(r["kind"], 'INTERDISCIPLINARY_DEFENSIVE_FABRIC')
        self.assertEqual(r["binding"], 'human_origin_threat_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1161, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1161, {"canonical_name": "OTHER"})
    def test_cap_1162(self):
        r = tranche.run(1162, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HUMAN_HARM_ONTOLOGY')
        self.assertEqual(r["kind"], 'ONTOLOGY')
        self.assertEqual(r["binding"], 'human_harm_ontology')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1162, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1162, {"canonical_name": "OTHER"})
    def test_cap_1163(self):
        r = tranche.run(1163, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PHILOSOPHY_OF_EVIL_ENGINE')
        self.assertEqual(r["kind"], 'INTERPRETIVE_DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'philosophy_of_evil_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1163, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1163, {"canonical_name": "OTHER"})
    def test_cap_1164(self):
        r = tranche.run(1164, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THEOLOGY_OF_EVIL_ENGINE')
        self.assertEqual(r["kind"], 'THEOLOGICAL_DOMAIN_ENGINE')
        self.assertEqual(r["binding"], 'theology_of_evil_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1164, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1164, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
