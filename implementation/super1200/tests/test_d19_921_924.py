#!/usr/bin/env python3
"""Negative tests for D19 921-924. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_921_924 as tranche


class D19Tranche921924Tests(unittest.TestCase):
    def test_cap_0921(self):
        r = tranche.run(921, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HOST_INTRUSION_DETECTION_FABRIC')
        self.assertEqual(r["kind"], 'DEFENSIVE_SECURITY_FABRIC')
        self.assertEqual(r["binding"], 'host_intrusion_detection_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(921, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(921, {"canonical_name": "OTHER"})
    def test_cap_0922(self):
        r = tranche.run(922, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROCESS_BEHAVIOR_BASELINE')
        self.assertEqual(r["kind"], 'BASELINE')
        self.assertEqual(r["binding"], 'process_behavior_baseline')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(922, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(922, {"canonical_name": "OTHER"})
    def test_cap_0923(self):
        r = tranche.run(923, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROCESS_ANOMALY_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'process_anomaly_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(923, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(923, {"canonical_name": "OTHER"})
    def test_cap_0924(self):
        r = tranche.run(924, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FILESYSTEM_INTEGRITY_MONITOR')
        self.assertEqual(r["kind"], 'MONITOR')
        self.assertEqual(r["binding"], 'filesystem_integrity_monitor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(924, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(924, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
