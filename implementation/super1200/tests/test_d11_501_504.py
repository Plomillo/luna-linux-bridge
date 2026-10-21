#!/usr/bin/env python3
"""Negative tests for D11 501-504. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d11_501_504 as tranche


class D11Tranche501504Tests(unittest.TestCase):
    def test_cap_0501(self):
        r = tranche.run(501, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CURIOSITY_ENGINE')
        self.assertEqual(r["kind"], 'RESEARCH_ORCHESTRATOR')
        self.assertEqual(r["binding"], 'curiosity_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(501, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(501, {"canonical_name": "OTHER"})
    def test_cap_0502(self):
        r = tranche.run(502, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'QUESTION_GENERATOR')
        self.assertEqual(r["kind"], 'REASONING_ENGINE')
        self.assertEqual(r["binding"], 'question_generator')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(502, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(502, {"canonical_name": "OTHER"})
    def test_cap_0503(self):
        r = tranche.run(503, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'UNKNOWN_TO_RESEARCH_PIPELINE')
        self.assertEqual(r["kind"], 'WORKFLOW')
        self.assertEqual(r["binding"], 'unknown_to_research_pipeline')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(503, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(503, {"canonical_name": "OTHER"})
    def test_cap_0504(self):
        r = tranche.run(504, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'RESEARCH_PRIORITY_ENGINE')
        self.assertEqual(r["kind"], 'DECISION_ENGINE')
        self.assertEqual(r["binding"], 'research_priority_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(504, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(504, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
