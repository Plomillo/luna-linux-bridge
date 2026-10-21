#!/usr/bin/env python3
"""Negative tests for D08 357-360. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_357_360 as tranche


class D08Tranche357360Tests(unittest.TestCase):
    def test_cap_0357(self):
        r = tranche.run(357, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MULTIPART_ARCHIVE')
        self.assertEqual(r["kind"], 'ARCHIVE_ENGINE')
        self.assertEqual(r["binding"], 'multipart_archive')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(357, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(357, {"canonical_name": "OTHER"})
    def test_cap_0358(self):
        r = tranche.run(358, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ERROR_RECOVERY_RECORDS')
        self.assertEqual(r["kind"], 'ARCHIVE_RECOVERY')
        self.assertEqual(r["binding"], 'error_recovery_records')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(358, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(358, {"canonical_name": "OTHER"})
    def test_cap_0359(self):
        r = tranche.run(359, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TRANSPORT_OPTIMIZER')
        self.assertEqual(r["kind"], 'PLANNER')
        self.assertEqual(r["binding"], 'transport_optimizer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(359, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(359, {"canonical_name": "OTHER"})
    def test_cap_0360(self):
        r = tranche.run(360, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'COMPRESSION_PARETO_SELECTOR')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'compression_pareto_selector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(360, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(360, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
