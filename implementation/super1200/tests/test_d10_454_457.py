#!/usr/bin/env python3
"""Negative tests for D10 454-457. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d10_454_457 as tranche


class D10Tranche454457Tests(unittest.TestCase):
    def test_cap_0454(self):
        r = tranche.run(454, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LSP_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'lsp_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(454, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(454, {"canonical_name": "OTHER"})
    def test_cap_0455(self):
        r = tranche.run(455, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FORMATTER_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'formatter_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(455, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(455, {"canonical_name": "OTHER"})
    def test_cap_0456(self):
        r = tranche.run(456, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DEBUGGER_PROTOCOL_PROVIDER')
        self.assertEqual(r["kind"], 'PROVIDER_INTERFACE')
        self.assertEqual(r["binding"], 'debugger_protocol_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(456, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(456, {"canonical_name": "OTHER"})
    def test_cap_0457(self):
        r = tranche.run(457, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PACKAGE_MANAGER_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'package_manager_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(457, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(457, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
