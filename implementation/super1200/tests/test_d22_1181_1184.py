#!/usr/bin/env python3
"""Negative tests for D22 1181-1184. Fail-closed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d22_1181_1184 as tranche


class D22Tranche11811184Tests(unittest.TestCase):
    def test_cap_1181(self):
        r = tranche.run(1181, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CYBERCRIME_ECOSYSTEM_MODEL')
        self.assertEqual(r["kind"], 'DEFENSIVE_ECOSYSTEM_GRAPH')
        self.assertEqual(r["binding"], 'cybercrime_ecosystem_model')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1181, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1181, {"canonical_name": "OTHER"})
    def test_cap_1182(self):
        r = tranche.run(1182, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'DARK_WEB_DEFENSIVE_INTELLIGENCE_INTERFACE')
        self.assertEqual(r["kind"], 'DEFENSIVE_INTELLIGENCE_INTERFACE')
        self.assertEqual(r["binding"], 'dark_web_defensive_intelligence_interface')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1182, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1182, {"canonical_name": "OTHER"})
    def test_cap_1183(self):
        r = tranche.run(1183, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'ILLICIT_MARKET_SIGNAL_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYTICS_ENGINE')
        self.assertEqual(r["binding"], 'illicit_market_signal_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1183, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1183, {"canonical_name": "OTHER"})
    def test_cap_1184(self):
        r = tranche.run(1184, {"probe": "catalog"})
        self.assertEqual(r["canonical_name"], 'CAMPAIGN_INTENT_ANALYZER')
        self.assertEqual(r["kind"], 'DEFENSIVE_ANALYSIS_ENGINE')
        self.assertEqual(r["binding"], 'campaign_intent_analyzer')
        self.assertFalse(r["certification_granted"])
        self.assertTrue(r["hardening"])
        bad = tranche.run(1184, None)
        self.assertEqual(bad["error"], "missing_ctx")
        self.assertFalse(bad["certification_granted"])
        with self.assertRaises(ValueError):
            tranche.run(1184, {"canonical_name": "OTHER"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
