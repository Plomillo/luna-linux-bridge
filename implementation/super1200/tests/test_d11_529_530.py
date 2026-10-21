#!/usr/bin/env python3
"""Negative tests for D11 529-530. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_529_530 as tranche


class D11Tranche529530Tests(unittest.TestCase):
    def test_cap_0529(self):
        r = tranche.run(529, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DOMAIN_VALIDATOR_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'domain_validator_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(529, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(529, {"canonical_name": "OTHER"})
    def test_cap_0530(self):
        r = tranche.run(530, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DISCIPLINE_CONFIDENCE_VECTOR')
        self.assertEqual(r["kind"], 'EPISTEMIC_METRIC')
        self.assertEqual(r["binding"], 'discipline_confidence_vector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(530, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(530, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
