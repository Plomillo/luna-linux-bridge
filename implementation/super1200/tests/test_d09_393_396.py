#!/usr/bin/env python3
"""Negative tests for D09 393-396. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d09_393_396 as tranche


class D09Tranche393396Tests(unittest.TestCase):
    def test_cap_0393(self):
        r = tranche.run(393, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ANDROID_NATIVE_MODEL_RUNTIME')
        self.assertEqual(r["kind"], 'MODEL_RUNTIME')
        self.assertEqual(r["binding"], 'android_native_model_runtime')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(393, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(393, {"canonical_name": "OTHER"})
    def test_cap_0394(self):
        r = tranche.run(394, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ONNX_RUNTIME_MOBILE')
        self.assertEqual(r["kind"], 'EXT_LIBRARY_RUNTIME')
        self.assertEqual(r["binding"], 'onnx_runtime_mobile')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(394, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(394, {"canonical_name": "OTHER"})
    def test_cap_0395(self):
        r = tranche.run(395, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'EXECUTORCH_PROVIDER')
        self.assertEqual(r["kind"], 'EXT_LIBRARY_RUNTIME')
        self.assertEqual(r["binding"], 'executorch_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(395, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(395, {"canonical_name": "OTHER"})
    def test_cap_0396(self):
        r = tranche.run(396, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'GGUF_ANDROID_PROVIDER')
        self.assertEqual(r["kind"], 'MODEL_RUNTIME_PROVIDER')
        self.assertEqual(r["binding"], 'gguf_android_provider')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(396, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(396, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
