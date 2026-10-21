#!/usr/bin/env python3
"""Negative tests for D08 301-304. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_301_304 as tranche


class D08Tranche301304Tests(unittest.TestCase):
    def test_cap_0301(self):
        r = tranche.run(301, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLAIM_REGISTRY')
        self.assertEqual(r["kind"], 'EPISTEMIC_REGISTRY')
        self.assertEqual(r["binding"], 'claim_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(301, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(301, {"canonical_name": "OTHER"})
    def test_cap_0302(self):
        r = tranche.run(302, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLAIM_IDENTITY')
        self.assertEqual(r["kind"], 'IDENTITY_PRIMITIVE')
        self.assertEqual(r["binding"], 'claim_identity')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(302, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(302, {"canonical_name": "OTHER"})
    def test_cap_0303(self):
        r = tranche.run(303, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLAIM_EVIDENCE_GRAPH')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'claim_evidence_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(303, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(303, {"canonical_name": "OTHER"})
    def test_cap_0304(self):
        r = tranche.run(304, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLAIM_SUPPORT')
        self.assertEqual(r["kind"], 'RELATION_TYPE')
        self.assertEqual(r["binding"], 'claim_support')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(304, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(304, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
