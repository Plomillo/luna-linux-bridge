#!/usr/bin/env python3
"""Negative tests for D09 401-404. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_401_404 as tranche


class D09Tranche401404Tests(unittest.TestCase):
    def test_cap_0401(self):
        r = tranche.run(401, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OS_FACTORY')
        self.assertEqual(r["kind"], 'OS_FACTORY')
        self.assertEqual(r["binding"], 'os_factory')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(401, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(401, {"canonical_name": "OTHER"})
    def test_cap_0402(self):
        r = tranche.run(402, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'KERNEL_BUILD_ENGINE')
        self.assertEqual(r["kind"], 'BUILD_ENGINE')
        self.assertEqual(r["binding"], 'kernel_build_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(402, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(402, {"canonical_name": "OTHER"})
    def test_cap_0403(self):
        r = tranche.run(403, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LINUX_KERNEL_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_OS_COMPONENT')
        self.assertEqual(r["binding"], 'linux_kernel_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(403, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(403, {"canonical_name": "OTHER"})
    def test_cap_0404(self):
        r = tranche.run(404, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INIT_SYSTEM_PROVIDER')
        self.assertEqual(r["kind"], 'PROVIDER_INTERFACE')
        self.assertEqual(r["binding"], 'init_system_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(404, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(404, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
