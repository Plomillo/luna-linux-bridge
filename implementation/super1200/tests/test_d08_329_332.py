#!/usr/bin/env python3
"""Negative tests for D08 329-332. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_329_332 as tranche


class D08Tranche329332Tests(unittest.TestCase):
    def test_cap_0329(self):
        r = tranche.run(329, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HISTORICAL_CLAIM_GRAPH')
        self.assertEqual(r["kind"], 'GRAPH')
        self.assertEqual(r["binding"], 'historical_claim_graph')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(329, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(329, {"canonical_name": "OTHER"})
    def test_cap_0330(self):
        r = tranche.run(330, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANACHRONISM_DETECTOR')
        self.assertEqual(r["kind"], 'DOMAIN_VALIDATOR')
        self.assertEqual(r["binding"], 'anachronism_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(330, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(330, {"canonical_name": "OTHER"})
    def test_cap_0331(self):
        r = tranche.run(331, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPRESSION_FABRIC')
        self.assertEqual(r["kind"], 'COMPRESSION_FABRIC')
        self.assertEqual(r["binding"], 'compression_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(331, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(331, {"canonical_name": "OTHER"})
    def test_cap_0332(self):
        r = tranche.run(332, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARCHIVE_CLASSIFIER')
        self.assertEqual(r["kind"], 'CLASSIFIER')
        self.assertEqual(r["binding"], 'archive_classifier')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(332, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(332, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
