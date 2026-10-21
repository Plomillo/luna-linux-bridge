#!/usr/bin/env python3
"""Negative tests for D22 1153-1156. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1153_1156 as tranche


class D22Tranche11531156Tests(unittest.TestCase):
    def test_cap_1153(self):
        r = tranche.run(1153, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_KNOWLEDGE_LOCAL_CACHE')
        self.assertEqual(r["kind"], 'CACHE')
        self.assertEqual(r["binding"], 'threat_knowledge_local_cache')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1153, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1153, {"canonical_name": "OTHER"})
    def test_cap_1154(self):
        r = tranche.run(1154, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_KNOWLEDGE_INCREMENTAL_UPDATE')
        self.assertEqual(r["kind"], 'UPDATE_ENGINE')
        self.assertEqual(r["binding"], 'threat_knowledge_incremental_update')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1154, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1154, {"canonical_name": "OTHER"})
    def test_cap_1155(self):
        r = tranche.run(1155, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_INTELLIGENCE_PROVENANCE')
        self.assertEqual(r["kind"], 'PROVENANCE_ENGINE')
        self.assertEqual(r["binding"], 'threat_intelligence_provenance')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1155, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1155, {"canonical_name": "OTHER"})
    def test_cap_1156(self):
        r = tranche.run(1156, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'THREAT_INTELLIGENCE_CONFIDENCE')
        self.assertEqual(r["kind"], 'EPISTEMIC_ENGINE')
        self.assertEqual(r["binding"], 'threat_intelligence_confidence')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1156, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1156, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
