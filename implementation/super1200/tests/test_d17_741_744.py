#!/usr/bin/env python3
"""Negative tests for D17 741-744. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d17_741_744 as tranche


class D17Tranche741744Tests(unittest.TestCase):
    def test_cap_0741(self):
        r = tranche.run(741, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LIFETIME_ARCHITECTURE_FABRIC')
        self.assertEqual(r["kind"], 'LONGEVITY_FABRIC')
        self.assertEqual(r["binding"], 'lifetime_architecture_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(741, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(741, {"canonical_name": "OTHER"})
    def test_cap_0742(self):
        r = tranche.run(742, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TECHNOLOGY_OBSOLESCENCE_WATCH')
        self.assertEqual(r["kind"], 'MONITOR')
        self.assertEqual(r["binding"], 'technology_obsolescence_watch')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(742, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(742, {"canonical_name": "OTHER"})
    def test_cap_0743(self):
        r = tranche.run(743, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CAPABILITY_SUCCESSION_ENGINE')
        self.assertEqual(r["kind"], 'EVOLUTION_ENGINE')
        self.assertEqual(r["binding"], 'capability_succession_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(743, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(743, {"canonical_name": "OTHER"})
    def test_cap_0744(self):
        r = tranche.run(744, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FORMAT_LONGEVITY_ENGINE')
        self.assertEqual(r["kind"], 'LONGEVITY_ENGINE')
        self.assertEqual(r["binding"], 'format_longevity_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(744, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(744, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
