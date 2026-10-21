#!/usr/bin/env python3
"""Negative tests for D07 287-290. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_287_290 as tranche


class D07Tranche287290Tests(unittest.TestCase):
    def test_cap_0287(self):
        r = tranche.run(287, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CORPUS_MANAGER')
        self.assertEqual(r["kind"], 'DATA_MANAGER')
        self.assertEqual(r["binding"], 'corpus_manager')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(287, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(287, {"canonical_name": "OTHER"})
    def test_cap_0288(self):
        r = tranche.run(288, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'INTERVIEW_TRANSCRIPTION')
        self.assertEqual(r["kind"], 'WORKFLOW')
        self.assertEqual(r["binding"], 'interview_transcription')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(288, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(288, {"canonical_name": "OTHER"})
    def test_cap_0289(self):
        r = tranche.run(289, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CODING_ENGINE')
        self.assertEqual(r["kind"], 'QUALITATIVE_ENGINE')
        self.assertEqual(r["binding"], 'coding_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(289, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(289, {"canonical_name": "OTHER"})
    def test_cap_0290(self):
        r = tranche.run(290, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CODEBOOK_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'codebook_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(290, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(290, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
