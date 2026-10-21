#!/usr/bin/env python3
"""Negative tests for D22 1113-1116. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1113_1116 as tranche


class D22Tranche11131116Tests(unittest.TestCase):
    def test_cap_1113(self):
        r = tranche.run(1113, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_PRESSURE_MONITOR')
        self.assertEqual(r["kind"], 'MONITOR')
        self.assertEqual(r["binding"], 'quarantine_pressure_monitor')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1113, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1113, {"canonical_name": "OTHER"})
    def test_cap_1114(self):
        r = tranche.run(1114, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_BACKLOG_ENGINE')
        self.assertEqual(r["kind"], 'PRIORITY_ENGINE')
        self.assertEqual(r["binding"], 'quarantine_backlog_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1114, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1114, {"canonical_name": "OTHER"})
    def test_cap_1115(self):
        r = tranche.run(1115, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_STALENESS_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'quarantine_staleness_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1115, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1115, {"canonical_name": "OTHER"})
    def test_cap_1116(self):
        r = tranche.run(1116, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUARANTINE_AUTO_ESCALATION')
        self.assertEqual(r["kind"], 'ESCALATION_ENGINE')
        self.assertEqual(r["binding"], 'quarantine_auto_escalation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1116, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1116, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
