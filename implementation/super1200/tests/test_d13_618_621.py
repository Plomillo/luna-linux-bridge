#!/usr/bin/env python3
"""Negative tests for D13 618-621. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d13_618_621 as tranche


class D13Tranche618621Tests(unittest.TestCase):
    def test_cap_0618(self):
        r = tranche.run(618, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXECUTABLE_EXAMPLE_ENGINE')
        self.assertEqual(r["kind"], 'TESTABLE_CONTENT_ENGINE')
        self.assertEqual(r["binding"], 'executable_example_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(618, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(618, {"canonical_name": "OTHER"})
    def test_cap_0619(self):
        r = tranche.run(619, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DOCUMENTATION_CI')
        self.assertEqual(r["kind"], 'CI_FABRIC')
        self.assertEqual(r["binding"], 'documentation_ci')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(619, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(619, {"canonical_name": "OTHER"})
    def test_cap_0620(self):
        r = tranche.run(620, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DOC_CODE_SYNCHRONIZATION')
        self.assertEqual(r["kind"], 'DOCUMENTATION_ENGINE')
        self.assertEqual(r["binding"], 'doc_code_synchronization')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(620, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(620, {"canonical_name": "OTHER"})
    def test_cap_0621(self):
        r = tranche.run(621, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DOCUMENTATION_DRIFT_DETECTOR')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'documentation_drift_detector')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(621, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(621, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
