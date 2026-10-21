#!/usr/bin/env python3
"""Negative tests for D19 881-884. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_881_884 as tranche


class D19Tranche881884Tests(unittest.TestCase):
    def test_cap_0881(self):
        r = tranche.run(881, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_DEFENSE_FABRIC')
        self.assertEqual(r["kind"], 'DEFENSIVE_SECURITY_FABRIC')
        self.assertEqual(r["binding"], 'malware_defense_fabric')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(881, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(881, {"canonical_name": "OTHER"})
    def test_cap_0882(self):
        r = tranche.run(882, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SIGNATURE_SCANNER_INTERFACE')
        self.assertEqual(r["kind"], 'PROVIDER_INTERFACE')
        self.assertEqual(r["binding"], 'signature_scanner_interface')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(882, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(882, {"canonical_name": "OTHER"})
    def test_cap_0883(self):
        r = tranche.run(883, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CLAMAV_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_SECURITY_ENGINE')
        self.assertEqual(r["binding"], 'clamav_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(883, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(883, {"canonical_name": "OTHER"})
    def test_cap_0884(self):
        r = tranche.run(884, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'YARA_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_SECURITY_LIBRARY_TOOL')
        self.assertEqual(r["binding"], 'yara_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(884, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(884, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
