#!/usr/bin/env python3
"""Negative tests for D07 247-250. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_247_250 as tranche


class D07Tranche247250Tests(unittest.TestCase):
    def test_cap_0247(self):
        r = tranche.run(247, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CROSS_MODEL_VALIDATION')
        self.assertEqual(r["kind"], 'VALIDATION_ENGINE')
        self.assertEqual(r["binding"], 'cross_model_validation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(247, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(247, {"canonical_name": "OTHER"})
    def test_cap_0248(self):
        r = tranche.run(248, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MODEL_DISAGREEMENT_ANALYZER')
        self.assertEqual(r["kind"], 'ANALYZER')
        self.assertEqual(r["binding"], 'model_disagreement_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(248, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(248, {"canonical_name": "OTHER"})
    def test_cap_0249(self):
        r = tranche.run(249, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MULTI_AGENT_TRACE')
        self.assertEqual(r["kind"], 'TRACE_ENGINE')
        self.assertEqual(r["binding"], 'multi_agent_trace')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(249, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(249, {"canonical_name": "OTHER"})
    def test_cap_0250(self):
        r = tranche.run(250, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MULTI_AGENT_PROVENANCE')
        self.assertEqual(r["kind"], 'PROVENANCE_ENGINE')
        self.assertEqual(r["binding"], 'multi_agent_provenance')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(250, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(250, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
