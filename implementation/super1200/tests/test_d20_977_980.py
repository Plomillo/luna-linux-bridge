#!/usr/bin/env python3
"""Negative tests for D20 977-980. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d20_977_980 as tranche


class D20Tranche977980Tests(unittest.TestCase):
    def test_cap_0977(self):
        r = tranche.run(977, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FILESYSTEM_BEHAVIOR_RECORDER')
        self.assertEqual(r["kind"], 'FORENSIC_RECORDER')
        self.assertEqual(r["binding"], 'filesystem_behavior_recorder')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(977, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(977, {"canonical_name": "OTHER"})
    def test_cap_0978(self):
        r = tranche.run(978, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROCESS_BEHAVIOR_RECORDER')
        self.assertEqual(r["kind"], 'FORENSIC_RECORDER')
        self.assertEqual(r["binding"], 'process_behavior_recorder')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(978, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(978, {"canonical_name": "OTHER"})
    def test_cap_0979(self):
        r = tranche.run(979, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PERSISTENCE_BEHAVIOR_RECORDER')
        self.assertEqual(r["kind"], 'FORENSIC_RECORDER')
        self.assertEqual(r["binding"], 'persistence_behavior_recorder')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(979, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(979, {"canonical_name": "OTHER"})
    def test_cap_0980(self):
        r = tranche.run(980, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'BEHAVIOR_TIMELINE')
        self.assertEqual(r["kind"], 'FORENSIC_TIMELINE')
        self.assertEqual(r["binding"], 'behavior_timeline')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(980, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(980, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
