#!/usr/bin/env python3
"""Negative tests for D15 669-672. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d15_669_672 as tranche


class D15Tranche669672Tests(unittest.TestCase):
    def test_cap_0669(self):
        r = tranche.run(669, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GPU_HEALTH_DIAGNOSTICS')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'gpu_health_diagnostics')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(669, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(669, {"canonical_name": "OTHER"})
    def test_cap_0670(self):
        r = tranche.run(670, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RAM_DIAGNOSTICS')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'ram_diagnostics')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(670, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(670, {"canonical_name": "OTHER"})
    def test_cap_0671(self):
        r = tranche.run(671, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'STORAGE_HEALTH_ENGINE')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'storage_health_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(671, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(671, {"canonical_name": "OTHER"})
    def test_cap_0672(self):
        r = tranche.run(672, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FILESYSTEM_HEALTH_ENGINE')
        self.assertEqual(r["kind"], 'DIAGNOSTIC_ENGINE')
        self.assertEqual(r["binding"], 'filesystem_health_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(672, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(672, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
