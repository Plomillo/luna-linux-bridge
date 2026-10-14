import concurrent.futures
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "implementation/super1200/domains/D04_authorization_controls.py"
spec = importlib.util.spec_from_file_location("d04_authorization_controls_tests", MODULE_PATH)
controls = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = controls
spec.loader.exec_module(controls)

PROOF_HASH = "a" * 64
PROVENANCE_HASH = "b" * 64


class D04AuthorizationControlsTests(unittest.TestCase):
    def test_single_use_authorization_consumes_nonce_atomically_and_denies_replay(self):
        registry = controls.SingleUseAuthorizationRegistry()
        def consume(_):
            return registry.consume(nonce="nonce-01", authorization_id="auth-01",
                subject="agent:deploy", action="publish", resource="artifact:7",
                now_utc="2026-10-13T10:30:00Z", expires_at_utc="2026-10-13T11:00:00Z",
                proof_sha256=PROOF_HASH)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(consume, range(16)))
        self.assertEqual(sum(item["decision"] == "ALLOW" for item in results), 1)
        self.assertEqual(sum(item["reason"] == "authorization_nonce_replay" for item in results), 15)
        receipt = registry.inspect("nonce-01")
        self.assertEqual(receipt["sequence"], 1)
        self.assertEqual(receipt["proof_sha256"], PROOF_HASH)
        self.assertEqual(receipt["event_sha256"], controls.digest({k:v for k,v in receipt.items() if k != "event_sha256"}))
        expired = registry.consume(nonce="nonce-02", authorization_id="auth-02",
            subject="agent:deploy", action="publish", resource="artifact:7",
            now_utc="2026-10-13T11:00:00Z", expires_at_utc="2026-10-13T11:00:00Z",
            proof_sha256=PROOF_HASH)
        self.assertEqual(expired["decision"], "DENY")
        self.assertEqual(len(registry.events), 1)

    def test_revocation_registry_is_append_only_effective_time_aware_and_hash_chained(self):
        registry = controls.RevocationRegistry()
        first = registry.revoke(revocation_id="rev-01", target_id="lease-01", issuer="root:security",
            reason="incident", effective_at_utc="2026-10-13T11:00:00Z", provenance_sha256=PROVENANCE_HASH)
        self.assertEqual(first["status"], "RECORDED")
        before = registry.is_revoked("lease-01", now_utc="2026-10-13T10:59:59Z")
        self.assertFalse(before["revoked"])
        after = registry.is_revoked("lease-01", now_utc="2026-10-13T11:00:00Z")
        self.assertTrue(after["revoked"])
        self.assertEqual(after["effective_revocations"][0]["reason"], "incident")
        duplicate = registry.revoke(revocation_id="rev-01", target_id="lease-01", issuer="root:security",
            reason="incident", effective_at_utc="2026-10-13T11:00:00Z", provenance_sha256=PROVENANCE_HASH)
        self.assertEqual(duplicate["status"], "IDEMPOTENT")
        with self.assertRaisesRegex(ValueError, "revocation_id_collision"):
            registry.revoke(revocation_id="rev-01", target_id="lease-other", issuer="root:security",
                reason="different", effective_at_utc="2026-10-13T11:00:00Z", provenance_sha256=PROVENANCE_HASH)
        registry.revoke(revocation_id="rev-02", target_id="auth-02", issuer="root:security",
            reason="key compromise", effective_at_utc="2026-10-13T12:00:00Z", provenance_sha256="c" * 64)
        self.assertEqual(registry.validate_chain()["status"], "PASS")
        self.assertEqual(registry.validate_chain()["event_count"], 2)

    def test_separation_of_duties_requires_distinct_actors_and_forbids_privilege_conflicts(self):
        assignments = {
            "executor": {"actor": "agent:executor", "permissions": ["materialize", "write_evidence"]},
            "verifier": {"actor": "agent:verifier", "permissions": ["read_source", "run_tests"]},
            "g23": {"actor": "agent:g23", "permissions": ["read_source", "run_tests", "write_validation"]},
            "g24": {"actor": "agent:g24", "permissions": ["read_source", "run_tests", "write_certification"]},
        }
        result = controls.validate_separation_of_duties(assignments)
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["reasons"], [])
        reused = dict(assignments, g24=dict(assignments["g24"], actor="agent:g23"))
        denied = controls.validate_separation_of_duties(reused)
        self.assertEqual(denied["decision"], "DENY")
        self.assertIn("actor_reused_across_roles:g23:g24", denied["reasons"])
        conflicted = dict(assignments, g23=dict(assignments["g23"], permissions=["read_source", "certify_g24"]))
        self.assertIn("forbidden_privilege_for_role:g23:certify_g24",
                      controls.validate_separation_of_duties(conflicted)["reasons"])
        self.assertIn("role_assignment_missing:verifier",
                      controls.validate_separation_of_duties({"executor": assignments["executor"]})["reasons"])

    def test_two_man_rule_applies_threshold_only_to_configured_risks_and_checks_signatures_expiry(self):
        provider = controls.TwoManRuleProvider(thresholds={"production-release": 2}, default_threshold=1)
        request = {"request_id": "req-01", "risk": "production-release", "action": "publish", "resource": "artifact:7"}
        request_hash = controls.digest(request)
        def approval(actor, key_id, expires="2026-10-13T11:00:00Z", signature=None):
            return {"schema": "SUPER1200_TWO_MAN_APPROVAL/1", "actor": actor, "key_id": key_id,
                "request_sha256": request_hash, "issued_at_utc": "2026-10-13T10:00:00Z",
                "expires_at_utc": expires, "signature": {"algorithm": "TEST", "value": signature or ("sig-" + actor)}}
        verifier = lambda item, payload: item.get("signature", {}).get("value") == "sig-" + item.get("actor", "")
        pair = [approval("reviewer-a", "key-a"), approval("reviewer-b", "key-b")]
        allowed = provider.evaluate(request, approvals=pair, now_utc="2026-10-13T10:30:00Z", signature_verifier=verifier)
        self.assertEqual(allowed["decision"], "ALLOW")
        self.assertEqual(allowed["threshold"], 2)
        self.assertEqual(allowed["valid_approval_count"], 2)
        insufficient = provider.evaluate(request, approvals=pair[:1], now_utc="2026-10-13T10:30:00Z", signature_verifier=verifier)
        self.assertEqual(insufficient["decision"], "DENY")
        self.assertIn("approval_threshold_not_met", insufficient["reasons"])
        duplicate_actor = provider.evaluate(request, approvals=[pair[0], approval("reviewer-a", "key-c")],
            now_utc="2026-10-13T10:30:00Z", signature_verifier=verifier)
        self.assertEqual(duplicate_actor["decision"], "DENY")
        self.assertIn("approval_actor_duplicate:1", duplicate_actor["reasons"])
        expired = provider.evaluate(request, approvals=[approval("reviewer-a", "key-a", "2026-10-13T10:20:00Z"),
            approval("reviewer-b", "key-b")], now_utc="2026-10-13T10:30:00Z", signature_verifier=verifier)
        self.assertIn("approval_not_current:0", expired["reasons"])
        low_risk = dict(request, request_id="req-low", risk="routine-maintenance")
        low_hash = controls.digest(low_risk)
        one = dict(approval("reviewer-c", "key-c"), request_sha256=low_hash)
        self.assertEqual(provider.evaluate(low_risk, approvals=[one], now_utc="2026-10-13T10:30:00Z",
            signature_verifier=verifier)["decision"], "ALLOW")


if __name__ == "__main__":
    unittest.main()
