#!/usr/bin/env python3
"""Negative tests for D07 251-254. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_251_254 as tranche


class D07Tranche251254Tests(unittest.TestCase):
    def test_cap_0251(self):
        r = tranche.run(251, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AUTHORSHIP_PROVENANCE_ENGINE')
        self.assertEqual(r["kind"], 'PROVENANCE_ENGINE')
        self.assertEqual(r["binding"], 'authorship_provenance_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(251, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(251, {"canonical_name": "OTHER"})
    def test_cap_0252(self):
        r = tranche.run(252, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GENERATION_RECEIPT')
        self.assertEqual(r["kind"], 'RECEIPT_SCHEMA')
        self.assertEqual(r["binding"], 'generation_receipt')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(252, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(252, {"canonical_name": "OTHER"})
    def test_cap_0253(self):
        r = tranche.run(253, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONTENT_BUILD_MANIFEST')
        self.assertEqual(r["kind"], 'MANIFEST')
        self.assertEqual(r["binding"], 'content_build_manifest')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(253, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(253, {"canonical_name": "OTHER"})
    def test_cap_0254(self):
        r = tranche.run(254, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROMPT_IDENTITY')
        self.assertEqual(r["kind"], 'IDENTITY_PRIMITIVE')
        self.assertEqual(r["binding"], 'prompt_identity')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(254, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(254, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
