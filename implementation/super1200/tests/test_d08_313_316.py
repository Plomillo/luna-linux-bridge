#!/usr/bin/env python3
"""Negative tests for D08 313-316. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d08_313_316 as tranche


class D08Tranche313316Tests(unittest.TestCase):
    def test_cap_0313(self):
        r = tranche.run(313, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EPISTEMIC_STATUS_MACHINE')
        self.assertEqual(r["kind"], 'STATE_MACHINE')
        self.assertEqual(r["binding"], 'epistemic_status_machine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(313, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(313, {"canonical_name": "OTHER"})
    def test_cap_0314(self):
        r = tranche.run(314, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HYPOTHESIS_REGISTRY')
        self.assertEqual(r["kind"], 'REGISTRY')
        self.assertEqual(r["binding"], 'hypothesis_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(314, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(314, {"canonical_name": "OTHER"})
    def test_cap_0315(self):
        r = tranche.run(315, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'HYPOTHESIS_TESTING')
        self.assertEqual(r["kind"], 'EVIDENCE_ENGINE')
        self.assertEqual(r["binding"], 'hypothesis_testing')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(315, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(315, {"canonical_name": "OTHER"})
    def test_cap_0316(self):
        r = tranche.run(316, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'FALSIFICATION_RECORD')
        self.assertEqual(r["kind"], 'LEDGER')
        self.assertEqual(r["binding"], 'falsification_record')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(316, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(316, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
