#!/usr/bin/env python3
"""Negative tests for D09 437-437. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_437_437 as tranche


class D09Tranche437437Tests(unittest.TestCase):
    def test_cap_0437(self):
        r = tranche.run(437, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'AUTOMATIC_ROLLBACK')
        self.assertEqual(r["kind"], 'RECOVERY_ENGINE')
        self.assertEqual(r["binding"], 'automatic_rollback')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(437, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(437, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
