#!/usr/bin/env python3
"""Negative tests for D10 450-453. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d10_450_453 as tranche


class D10Tranche450453Tests(unittest.TestCase):
    def test_cap_0450(self):
        r = tranche.run(450, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BYTECODE_VM_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'bytecode_vm_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(450, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(450, {"canonical_name": "OTHER"})
    def test_cap_0451(self):
        r = tranche.run(451, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INTERPRETER_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'interpreter_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(451, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(451, {"canonical_name": "OTHER"})
    def test_cap_0452(self):
        r = tranche.run(452, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPILER_FACTORY')
        self.assertEqual(r["kind"], 'FACTORY')
        self.assertEqual(r["binding"], 'compiler_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(452, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(452, {"canonical_name": "OTHER"})
    def test_cap_0453(self):
        r = tranche.run(453, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'JIT_PROVIDER')
        self.assertEqual(r["kind"], 'PROVIDER_INTERFACE')
        self.assertEqual(r["binding"], 'jit_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(453, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(453, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
