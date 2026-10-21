#!/usr/bin/env python3
"""Negative tests for D07 255-258. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_255_258 as tranche


class D07Tranche255258Tests(unittest.TestCase):
    def test_cap_0255(self):
        r = tranche.run(255, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONTEXT_MANIFEST')
        self.assertEqual(r["kind"], 'MANIFEST')
        self.assertEqual(r["binding"], 'context_manifest')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(255, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(255, {"canonical_name": "OTHER"})
    def test_cap_0256(self):
        r = tranche.run(256, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MODEL_IDENTITY')
        self.assertEqual(r["kind"], 'IDENTITY_PRIMITIVE')
        self.assertEqual(r["binding"], 'model_identity')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(256, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(256, {"canonical_name": "OTHER"})
    def test_cap_0257(self):
        r = tranche.run(257, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TOOL_CALL_MANIFEST')
        self.assertEqual(r["kind"], 'MANIFEST')
        self.assertEqual(r["binding"], 'tool_call_manifest')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(257, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(257, {"canonical_name": "OTHER"})
    def test_cap_0258(self):
        r = tranche.run(258, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SOURCE_MANIFEST')
        self.assertEqual(r["kind"], 'MANIFEST')
        self.assertEqual(r["binding"], 'source_manifest')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(258, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(258, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
