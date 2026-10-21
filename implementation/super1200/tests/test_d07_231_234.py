#!/usr/bin/env python3
"""Negative tests for D07 231-234. Fail-closed."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200/domains"))

import d07_231_234 as d07

class D07FirstTrancheTests:
    def test_cap_0231(self):
        r = d07.run(231, {"models": ["a", "b"]})
        assert r["canonical_name"] == "MULTI_AI_ARCHITECTURE_FACTORY"
        assert r["certification_granted"] is False
        bad = d07.run(231, None)
        assert "error" in bad

    def test_cap_0232(self):
        r = d07.run(232, {"nodes": [1, 2]})
        assert r["canonical_name"] == "AGENT_GRAPH_FACTORY"
        assert r["certification_granted"] is False

    def test_cap_0233(self):
        r = d07.run(233, {"routes": ["x"]})
        assert r["canonical_name"] == "ROUTER_FACTORY"
        assert r["certification_granted"] is False

    def test_cap_0234(self):
        r = d07.run(234, {"members": ["m1"]})
        assert r["canonical_name"] == "ENSEMBLE_ENGINE"
        assert r["certification_granted"] is False

if __name__ == "__main__":
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(D07FirstTrancheTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
