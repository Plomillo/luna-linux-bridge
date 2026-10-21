#!/usr/bin/env python3
"""Negative tests for D19 889-892. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d19_889_892 as tranche


class D19Tranche889892Tests(unittest.TestCase):
    def test_cap_0889(self):
        r = tranche.run(889, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FILE_REPUTATION_ENGINE')
        self.assertEqual(r["kind"], 'EVIDENCE_ENGINE')
        self.assertEqual(r["binding"], 'file_reputation_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(889, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(889, {"canonical_name": "OTHER"})
    def test_cap_0890(self):
        r = tranche.run(890, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HASH_REPUTATION_ENGINE')
        self.assertEqual(r["kind"], 'EVIDENCE_ENGINE')
        self.assertEqual(r["binding"], 'hash_reputation_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(890, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(890, {"canonical_name": "OTHER"})
    def test_cap_0891(self):
        r = tranche.run(891, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PACKER_DETECTOR')
        self.assertEqual(r["kind"], 'DETECTOR')
        self.assertEqual(r["binding"], 'packer_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(891, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(891, {"canonical_name": "OTHER"})
    def test_cap_0892(self):
        r = tranche.run(892, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'SCRIPT_MALWARE_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYZER')
        self.assertEqual(r["binding"], 'script_malware_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(892, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(892, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
