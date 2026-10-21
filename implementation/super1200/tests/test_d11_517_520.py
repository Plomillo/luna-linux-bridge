#!/usr/bin/env python3
"""Negative tests for D11 517-520. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_517_520 as tranche


class D11Tranche517520Tests(unittest.TestCase):
    def test_cap_0517(self):
        r = tranche.run(517, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DISCIPLINE_ONTOLOGY')
        self.assertEqual(r["kind"], 'ONTOLOGY')
        self.assertEqual(r["binding"], 'discipline_ontology')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(517, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(517, {"canonical_name": "OTHER"})
    def test_cap_0518(self):
        r = tranche.run(518, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'METHOD_ONTOLOGY')
        self.assertEqual(r["kind"], 'ONTOLOGY')
        self.assertEqual(r["binding"], 'method_ontology')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(518, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(518, {"canonical_name": "OTHER"})
    def test_cap_0519(self):
        r = tranche.run(519, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EVIDENCE_TYPE_ONTOLOGY')
        self.assertEqual(r["kind"], 'ONTOLOGY')
        self.assertEqual(r["binding"], 'evidence_type_ontology')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(519, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(519, {"canonical_name": "OTHER"})
    def test_cap_0520(self):
        r = tranche.run(520, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CROSS_DISCIPLINE_TRANSLATOR')
        self.assertEqual(r["kind"], 'SEMANTIC_ADAPTER')
        self.assertEqual(r["binding"], 'cross_discipline_translator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(520, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(520, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
