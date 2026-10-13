import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
RUNTIME_PATH = ROOT / "implementation/super1200/domains/D04_runtime.py"
spec = importlib.util.spec_from_file_location("d04_runtime_policy_tests", RUNTIME_PATH)
d04 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = d04
spec.loader.exec_module(d04)

POLICY_PATH = ROOT / "implementation/super1200/domains/D04_policy_governance.py"
policy_spec = importlib.util.spec_from_file_location("d04_policy_governance", POLICY_PATH)
gov = importlib.util.module_from_spec(policy_spec)
sys.modules[policy_spec.name] = gov
policy_spec.loader.exec_module(gov)


def policy(version="1", rules=None, **extra):
    value = {
        "schema": "SUPER1200_POLICY/1",
        "policy_id": "access-control",
        "version": version,
        "rules": rules if rules is not None else [
            {"id": "allow-owner", "effect": "ALLOW", "principal": "owner"},
            {"id": "deny-unknown", "effect": "DENY", "principal": "UNKNOWN"},
        ],
    }
    value.update(extra)
    return value


class D04PolicyGovernanceTests(unittest.TestCase):
    def test_policy_test_suite_covers_positive_negative_bypass_conflict_and_unknown(self):
        cases = [
            {"case_id": "positive-owner", "category": "positive", "expected_decision": "ALLOW", "input": {"principal": "owner"}},
            {"case_id": "negative-guest", "category": "negative", "expected_decision": "DENY", "input": {"principal": "guest"}},
            {"case_id": "bypass-missing-principal", "category": "bypass", "expected_decision": "DENY", "input": {}},
            {"case_id": "conflict-two-effects", "category": "conflict", "expected_decision": "DENY", "input": {"principal": "conflict"}},
            {"case_id": "unknown-engine-result", "category": "unknown", "expected_decision": "UNKNOWN", "input": {"principal": "UNKNOWN"}},
        ]
        def evaluator(_policy, item):
            principal = item.get("principal")
            if principal == "owner": return {"decision": "ALLOW"}
            if principal in {"guest", None, "conflict"}: return {"decision": "DENY"}
            return {"decision": "UNKNOWN"}
        result = gov.run_policy_test_suite(policy(), cases, evaluator)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["passed"], 5)
        self.assertEqual(set(result["coverage"]), {"positive", "negative", "bypass", "conflict", "unknown"})
        self.assertEqual(len(result["suite_sha256"]), 64)
        bad = [dict(c) for c in cases if c["category"] != "bypass"]
        with self.assertRaisesRegex(ValueError, "coverage_missing"):
            gov.run_policy_test_suite(policy(), bad, evaluator)
        with self.assertRaisesRegex(ValueError, "positive_case_must_expect_allow"):
            gov.run_policy_test_suite(policy(), [dict(cases[0], expected_decision="DENY"), *cases[1:]], evaluator)

    def test_policy_versioning_binds_hash_interval_and_explicit_supersession(self):
        registry = gov.PolicyVersionRegistry()
        v1 = policy("1", effective_owner="security")
        old = registry.register(v1, effective_from_utc="2026-01-01T00:00:00Z",
                                effective_until_utc="2026-06-01T00:00:00Z")
        v2 = policy("2", rules=[{"id":"allow-owner","effect":"ALLOW","principal":"owner"},
                               {"id":"deny-unknown","effect":"DENY","principal":"UNKNOWN"},
                               {"id":"deny-disabled","effect":"DENY","principal":"disabled"}])
        new = registry.register(v2, effective_from_utc="2026-06-01T00:00:00Z",
                                supersedes={"policy_id":"access-control","version":"1"})
        self.assertEqual(len(old["policy_sha256"]), 64)
        self.assertEqual(len(new["record_sha256"]), 64)
        self.assertEqual(registry.select("access-control", now_utc="2026-05-01T00:00:00Z")["policy"]["version"], "1")
        self.assertEqual(registry.select("access-control", now_utc="2026-07-01T00:00:00Z")["policy"]["version"], "2")
        self.assertEqual(registry.get("access-control", "1")["policy_sha256"], old["policy_sha256"])
        with self.assertRaisesRegex(ValueError, "policy_version_identity_immutable"):
            registry.register(policy("1", rules=[{"id":"rewritten","effect":"ALLOW"}]),
                              effective_from_utc="2026-01-01T00:00:00Z",
                              effective_until_utc="2026-06-01T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "policy_superseded_interval_must_be_closed"):
            gov.PolicyVersionRegistry().register(policy("3"), effective_from_utc="2026-07-01T00:00:00Z",
                supersedes={"policy_id":"access-control","version":"1"})

    def test_policy_semantic_diff_ignores_rule_order_and_reports_changed_decision_rules(self):
        before = policy("1", rules=[
            {"id":"allow-owner","effect":"ALLOW","principal":"owner"},
            {"id":"deny-guest","effect":"DENY","principal":"guest"},
        ])
        reordered = policy("1.1", rules=[
            {"id":"deny-guest","effect":"DENY","principal":"guest"},
            {"id":"allow-owner","effect":"ALLOW","principal":"owner"},
        ])
        no_change = gov.semantic_policy_diff(before, reordered)
        self.assertFalse(no_change["semantic_change"])
        self.assertEqual(no_change["affected_decision_rules"], [])
        after = policy("2", rules=[
            {"id":"allow-owner","effect":"DENY","principal":"owner"},
            {"id":"deny-guest","effect":"DENY","principal":"guest"},
            {"id":"deny-disabled","effect":"DENY","principal":"disabled"},
        ])
        diff = gov.semantic_policy_diff(before, after)
        self.assertTrue(diff["semantic_change"])
        self.assertEqual(diff["added_rule_ids"], ["deny-disabled"])
        self.assertEqual(diff["changed_rules"][0]["rule_id"], "allow-owner")
        self.assertEqual(diff["affected_decision_rules"], ["allow-owner", "deny-disabled"])
        with self.assertRaisesRegex(ValueError, "policy_diff_identity_mismatch"):
            gov.semantic_policy_diff(before, dict(after, policy_id="other-policy"))

    def test_policy_impact_analysis_propagates_semantic_changes_to_claims_tests_auths(self):
        graph = d04.EvidenceInvalidationGraph()
        for node in ("policy:access-control", "claim:owner", "test:owner-access", "auth:session",
                     "evidence:session-proof", "claim:unrelated"):
            graph.add_evidence(node)
        graph.add_dependency("policy:access-control", "claim:owner")
        graph.add_dependency("claim:owner", "test:owner-access")
        graph.add_dependency("claim:owner", "auth:session")
        graph.add_dependency("auth:session", "evidence:session-proof")
        diff = gov.semantic_policy_diff(
            policy("1", rules=[{"id":"allow-owner","effect":"ALLOW"}]),
            policy("2", rules=[{"id":"allow-owner","effect":"DENY"}]))
        impact = gov.analyze_policy_impact(graph, policy_node_id="policy:access-control", semantic_diff=diff)
        self.assertEqual(impact["status"], "IMPACT_ANALYZED")
        self.assertEqual(impact["affected_by_kind"]["claims"], ["claim:owner"])
        self.assertEqual(impact["affected_by_kind"]["tests"], ["test:owner-access"])
        self.assertEqual(impact["affected_by_kind"]["authorizations"], ["auth:session"])
        self.assertIn("evidence:session-proof", impact["recompute_ids"])
        self.assertIn("claim:unrelated", impact["preserved_ids"])
        unchanged = gov.analyze_policy_impact(graph, policy_node_id="policy:access-control",
            semantic_diff=gov.semantic_policy_diff(policy("1"), policy("1.1")))
        self.assertEqual(unchanged["recompute_ids"], [])
        self.assertIn("claim:owner", unchanged["preserved_ids"])


if __name__ == "__main__":
    unittest.main()
