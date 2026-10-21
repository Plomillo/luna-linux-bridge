#!/usr/bin/env python3
"""Negative tests for D10 446-449. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d10_446_449 as tranche


class D10Tranche446449Tests(unittest.TestCase):
    def test_cap_0446(self):
        r = tranche.run(446, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'IR_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'ir_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(446, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(446, {"canonical_name": "OTHER"})
    def test_cap_0447(self):
        r = tranche.run(447, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LLVM_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_COMPILER_INFRASTRUCTURE')
        self.assertEqual(r["binding"], 'llvm_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(447, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(447, {"canonical_name": "OTHER"})
    def test_cap_0448(self):
        r = tranche.run(448, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MLIR_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_COMPILER_INFRASTRUCTURE')
        self.assertEqual(r["binding"], 'mlir_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(448, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(448, {"canonical_name": "OTHER"})
    def test_cap_0449(self):
        r = tranche.run(449, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CODEGEN_ENGINE')
        self.assertEqual(r["kind"], 'COMPILER_ENGINE')
        self.assertEqual(r["binding"], 'codegen_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(449, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(449, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
