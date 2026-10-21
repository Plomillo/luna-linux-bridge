#!/usr/bin/env python3
"""Negative tests for D15 685-688. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d15_685_688 as tranche


class D15Tranche685688Tests(unittest.TestCase):
    def test_cap_0685(self):
        r = tranche.run(685, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CONFIGURATION_REPAIR_ENGINE')
        self.assertEqual(r["kind"], 'REPAIR_ENGINE')
        self.assertEqual(r["binding"], 'configuration_repair_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(685, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(685, {"canonical_name": "OTHER"})
    def test_cap_0686(self):
        r = tranche.run(686, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PACKAGE_REPAIR_ENGINE')
        self.assertEqual(r["kind"], 'REPAIR_ENGINE')
        self.assertEqual(r["binding"], 'package_repair_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(686, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(686, {"canonical_name": "OTHER"})
    def test_cap_0687(self):
        r = tranche.run(687, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BOOT_REPAIR_ENGINE')
        self.assertEqual(r["kind"], 'REPAIR_ENGINE')
        self.assertEqual(r["binding"], 'boot_repair_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(687, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(687, {"canonical_name": "OTHER"})
    def test_cap_0688(self):
        r = tranche.run(688, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FILESYSTEM_REPAIR_ORCHESTRATOR')
        self.assertEqual(r["kind"], 'REPAIR_ORCHESTRATOR')
        self.assertEqual(r["binding"], 'filesystem_repair_orchestrator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(688, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(688, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
