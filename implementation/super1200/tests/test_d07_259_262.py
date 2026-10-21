#!/usr/bin/env python3
"""Negative tests for D07 259-262. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_259_262 as tranche


class D07Tranche259262Tests(unittest.TestCase):
    def test_cap_0259(self):
        r = tranche.run(259, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'TRANSFORMATION_LOG')
        self.assertEqual(r["kind"], 'APPEND_ONLY_LOG')
        self.assertEqual(r["binding"], 'transformation_log')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(259, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(259, {"canonical_name": "OTHER"})
    def test_cap_0260(self):
        r = tranche.run(260, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OUTPUT_HASH')
        self.assertEqual(r["kind"], 'INTEGRITY_PRIMITIVE')
        self.assertEqual(r["binding"], 'output_hash')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(260, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(260, {"canonical_name": "OTHER"})
    def test_cap_0261(self):
        r = tranche.run(261, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OUTPUT_SIGNATURE')
        self.assertEqual(r["kind"], 'SIGNATURE_PRIMITIVE')
        self.assertEqual(r["binding"], 'output_signature')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(261, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(261, {"canonical_name": "OTHER"})
    def test_cap_0262(self):
        r = tranche.run(262, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARCHITECTURE_AUTHORSHIP_ATTESTATION')
        self.assertEqual(r["kind"], 'ATTESTATION_PATTERN')
        self.assertEqual(r["binding"], 'architecture_authorship_attestation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(262, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(262, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
