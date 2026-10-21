#!/usr/bin/env python3
"""Negative tests for D22 1129-1132. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1129_1132 as tranche


class D22Tranche11291132Tests(unittest.TestCase):
    def test_cap_1129(self):
        r = tranche.run(1129, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'MALWARE_TTP_KB')
        self.assertEqual(r["kind"], 'KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'malware_ttp_kb')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1129, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1129, {"canonical_name": "OTHER"})
    def test_cap_1130(self):
        r = tranche.run(1130, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ATTACK_KNOWLEDGE_ADAPTER')
        self.assertEqual(r["kind"], 'DATA_STANDARD_ADAPTER')
        self.assertEqual(r["binding"], 'attack_knowledge_adapter')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1130, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1130, {"canonical_name": "OTHER"})
    def test_cap_1131(self):
        r = tranche.run(1131, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'IOC_KNOWLEDGE_BASE')
        self.assertEqual(r["kind"], 'KNOWLEDGE_BASE')
        self.assertEqual(r["binding"], 'ioc_knowledge_base')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1131, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1131, {"canonical_name": "OTHER"})
    def test_cap_1132(self):
        r = tranche.run(1132, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'IOC_EXPIRATION_ENGINE')
        self.assertEqual(r["kind"], 'VALIDITY_ENGINE')
        self.assertEqual(r["binding"], 'ioc_expiration_engine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1132, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1132, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
