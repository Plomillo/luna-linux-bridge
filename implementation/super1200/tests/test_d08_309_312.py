#!/usr/bin/env python3
"""Negative tests for D08 309-312. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_309_312 as tranche


class D08Tranche309312Tests(unittest.TestCase):
    def test_cap_0309(self):
        r = tranche.run(309, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLAIM_SOURCE_QUALITY')
        self.assertEqual(r["kind"], 'EVIDENCE_ENGINE')
        self.assertEqual(r["binding"], 'claim_source_quality')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(309, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(309, {"canonical_name": "OTHER"})
    def test_cap_0310(self):
        r = tranche.run(310, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EVIDENCE_TRIANGULATION')
        self.assertEqual(r["kind"], 'EVIDENCE_ENGINE')
        self.assertEqual(r["binding"], 'evidence_triangulation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(310, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(310, {"canonical_name": "OTHER"})
    def test_cap_0311(self):
        r = tranche.run(311, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOURCE_INDEPENDENCE')
        self.assertEqual(r["kind"], 'INDEPENDENCE_ENGINE')
        self.assertEqual(r["binding"], 'source_independence')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(311, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(311, {"canonical_name": "OTHER"})
    def test_cap_0312(self):
        r = tranche.run(312, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOURCE_CONFLICT_RESOLUTION')
        self.assertEqual(r["kind"], 'CONFLICT_ENGINE')
        self.assertEqual(r["binding"], 'source_conflict_resolution')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(312, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(312, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
