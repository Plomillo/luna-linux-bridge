#!/usr/bin/env python3
"""Negative tests for D07 299-300. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_299_300 as tranche


class D07Tranche299300Tests(unittest.TestCase):
    def test_cap_0299(self):
        r = tranche.run(299, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EVIDENCE_LINKED_CODING')
        self.assertEqual(r["kind"], 'TRACEABILITY_ENGINE')
        self.assertEqual(r["binding"], 'evidence_linked_coding')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(299, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(299, {"canonical_name": "OTHER"})
    def test_cap_0300(self):
        r = tranche.run(300, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MIXED_METHODS_ENGINE')
        self.assertEqual(r["kind"], 'RESEARCH_ORCHESTRATOR')
        self.assertEqual(r["binding"], 'mixed_methods_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(300, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(300, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
