#!/usr/bin/env python3
"""Negative tests for D12 559-562. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_559_562 as tranche


class D12Tranche559562Tests(unittest.TestCase):
    def test_cap_0559(self):
        r = tranche.run(559, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'OPENAPI_REGISTRY')
        self.assertEqual(r["kind"], 'API_REGISTRY')
        self.assertEqual(r["binding"], 'openapi_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(559, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(559, {"canonical_name": "OTHER"})
    def test_cap_0560(self):
        r = tranche.run(560, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ASYNCAPI_REGISTRY')
        self.assertEqual(r["kind"], 'API_REGISTRY')
        self.assertEqual(r["binding"], 'asyncapi_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(560, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(560, {"canonical_name": "OTHER"})
    def test_cap_0561(self):
        r = tranche.run(561, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROTOBUF_REGISTRY')
        self.assertEqual(r["kind"], 'SCHEMA_REGISTRY')
        self.assertEqual(r["binding"], 'protobuf_registry')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(561, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(561, {"canonical_name": "OTHER"})
    def test_cap_0562(self):
        r = tranche.run(562, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GRPC_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_PROTOCOL_LIBRARY')
        self.assertEqual(r["binding"], 'grpc_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(562, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(562, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
