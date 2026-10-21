#!/usr/bin/env python3
"""Negative tests for D08 305-308. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_305_308 as tranche


class D08Tranche305308Tests(unittest.TestCase):
    def test_cap_0305(self):
        r = tranche.run(305, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLAIM_CONTRADICTION')
        self.assertEqual(r["kind"], 'RELATION_ENGINE')
        self.assertEqual(r["binding"], 'claim_contradiction')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(305, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(305, {"canonical_name": "OTHER"})
    def test_cap_0306(self):
        r = tranche.run(306, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLAIM_UNCERTAINTY')
        self.assertEqual(r["kind"], 'EPISTEMIC_PRIMITIVE')
        self.assertEqual(r["binding"], 'claim_uncertainty')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(306, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(306, {"canonical_name": "OTHER"})
    def test_cap_0307(self):
        r = tranche.run(307, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLAIM_SCOPE')
        self.assertEqual(r["kind"], 'EPISTEMIC_PRIMITIVE')
        self.assertEqual(r["binding"], 'claim_scope')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(307, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(307, {"canonical_name": "OTHER"})
    def test_cap_0308(self):
        r = tranche.run(308, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLAIM_TEMPORAL_VALIDITY')
        self.assertEqual(r["kind"], 'EPISTEMIC_PRIMITIVE')
        self.assertEqual(r["binding"], 'claim_temporal_validity')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(308, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(308, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
