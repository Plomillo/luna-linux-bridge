#!/usr/bin/env python3
"""Negative tests for D12 555-558. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_555_558 as tranche


class D12Tranche555558Tests(unittest.TestCase):
    def test_cap_0555(self):
        r = tranche.run(555, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'C4_ARCHITECTURE_VIEWS')
        self.assertEqual(r["kind"], 'DOCUMENTATION_VIEW')
        self.assertEqual(r["binding"], 'c4_architecture_views')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(555, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(555, {"canonical_name": "OTHER"})
    def test_cap_0556(self):
        r = tranche.run(556, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MACHINE_READABLE_ARCHITECTURE_DOCS')
        self.assertEqual(r["kind"], 'DOCUMENTATION_ENGINE')
        self.assertEqual(r["binding"], 'machine_readable_architecture_docs')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(556, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(556, {"canonical_name": "OTHER"})
    def test_cap_0557(self):
        r = tranche.run(557, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'LIVE_DEPENDENCY_DIAGRAMS')
        self.assertEqual(r["kind"], 'DOCUMENTATION_VIEW')
        self.assertEqual(r["binding"], 'live_dependency_diagrams')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(557, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(557, {"canonical_name": "OTHER"})
    def test_cap_0558(self):
        r = tranche.run(558, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ARCHITECTURE_DRIFT_DOC_CHECK')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'architecture_drift_doc_check')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(558, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(558, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
