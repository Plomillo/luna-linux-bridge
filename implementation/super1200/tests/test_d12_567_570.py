#!/usr/bin/env python3
"""Negative tests for D12 567-570. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d12_567_570 as tranche


class D12Tranche567570Tests(unittest.TestCase):
    def test_cap_0567(self):
        r = tranche.run(567, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'API_BACKWARD_COMPATIBILITY')
        self.assertEqual(r["kind"], 'GATE')
        self.assertEqual(r["binding"], 'api_backward_compatibility')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(567, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(567, {"canonical_name": "OTHER"})
    def test_cap_0568(self):
        r = tranche.run(568, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROTOCOL_STATE_MACHINE')
        self.assertEqual(r["kind"], 'STATE_MACHINE')
        self.assertEqual(r["binding"], 'protocol_state_machine')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(568, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(568, {"canonical_name": "OTHER"})
    def test_cap_0569(self):
        r = tranche.run(569, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'PROTOCOL_FORMAL_VERIFICATION')
        self.assertEqual(r["kind"], 'FORMAL_VALIDATION')
        self.assertEqual(r["binding"], 'protocol_formal_verification')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(569, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(569, {"canonical_name": "OTHER"})
    def test_cap_0570(self):
        r = tranche.run(570, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CAPABILITY_NEGOTIATION')
        self.assertEqual(r["kind"], 'PROTOCOL_ENGINE')
        self.assertEqual(r["binding"], 'capability_negotiation')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(570, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(570, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
