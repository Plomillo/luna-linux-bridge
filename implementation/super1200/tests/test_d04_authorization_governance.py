import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "implementation/super1200/domains/D04_authorization_governance.py"
spec = importlib.util.spec_from_file_location("d04_authorization_governance_tests", MODULE_PATH)
auth = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = auth
spec.loader.exec_module(auth)


def authorization_proof():
    proof = {
        "schema": "SUPER1200_AUTHORIZATION_PROOF/1",
        "proof_id": "proof-001",
        "subject": "agent:executor",
        "action": "deploy",
        "object": "release:artifact-7",
        "scope": {"environment": "staging", "capabilities": [109]},
        "issuer": "root:security",
        "issued_at_utc": "2026-10-13T10:00:00Z",
        "not_before_utc": "2026-10-13T10:00:00Z",
        "not_after_utc": "2026-10-13T11:00:00Z",
        "revocation_id": "revocation-001",
        "delegation": None,
        "provenance": {
            "operation_id": "op-001",
            "source_uri": "git+https://example.invalid/repo@abc123",
            "input_sha256": "a" * 64,
        },
        "signature": {"algorithm": "TEST-VERIFIER", "value": "test-signature"},
    }
    proof["proof_sha256"] = hashlib.sha256(auth.canonical_bytes(proof)).hexdigest()
    return proof


class D04AuthorizationGovernanceTests(unittest.TestCase):
    def test_authorization_proof_binds_request_signature_time_scope_and_revocation(self):
        proof = authorization_proof()
        request = {
            "subject": "agent:executor", "action": "deploy", "object": "release:artifact-7",
            "scope": {"environment": "staging", "capabilities": [109]},
        }
        result = auth.validate_authorization_proof(
            proof, request=request, now_utc="2026-10-13T10:30:00Z",
            signature_verifier=lambda _proof, payload: bool(payload) and _proof["signature"]["value"] == "test-signature",
            revocation_checker=lambda _proof_id, _issuer: False,
        )
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["revocation_status"], "NOT_REVOKED")
        self.assertEqual(len(result["proof_sha256"]), 64)
        scope_mismatch = dict(request, scope={"environment": "production", "capabilities": [109]})
        denied = auth.validate_authorization_proof(
            proof, request=scope_mismatch, now_utc="2026-10-13T10:30:00Z",
            signature_verifier=lambda *_: True, revocation_checker=lambda *_: False)
        self.assertEqual(denied["decision"], "DENY")
        self.assertIn("authorization_scope_mismatch", denied["reasons"])
        revoked = auth.validate_authorization_proof(
            proof, request=request, now_utc="2026-10-13T10:30:00Z",
            signature_verifier=lambda *_: True, revocation_checker=lambda *_: True)
        self.assertIn("authorization_revoked", revoked["reasons"])
        unknown_revocation = auth.validate_authorization_proof(
            proof, request=request, now_utc="2026-10-13T10:30:00Z",
            signature_verifier=lambda *_: True, revocation_checker=lambda *_: None)
        self.assertIn("revocation_status_unknown", unknown_revocation["reasons"])
        bad_signature = auth.validate_authorization_proof(
            proof, request=request, now_utc="2026-10-13T10:30:00Z",
            signature_verifier=lambda *_: False, revocation_checker=lambda *_: False)
        self.assertIn("authorization_signature_verification_failed", bad_signature["reasons"])
        expired = auth.validate_authorization_proof(
            proof, request=request, now_utc="2026-10-13T11:00:00Z",
            signature_verifier=lambda *_: True, revocation_checker=lambda *_: False)
        self.assertIn("authorization_expired", expired["reasons"])

    def test_capability_lease_enforces_actor_action_resource_time_revocation_and_consumption(self):
        registry = auth.CapabilityLeaseRegistry()
        lease = registry.grant(
            lease_id="lease-001", subject="agent:executor", capability="release.write",
            actions=["publish", "attest"], resources=["artifact:7", "artifact:8"],
            nonce="nonce-001", issuer="root:security",
            issued_at_utc="2026-10-13T10:00:00Z",
            not_before_utc="2026-10-13T10:00:00Z",
            not_after_utc="2026-10-13T11:00:00Z", max_uses=2)
        self.assertEqual(lease["schema"], "SUPER1200_CAPABILITY_LEASE/1")
        allow = registry.authorize("lease-001", subject="agent:executor", action="publish",
                                   resource="artifact:7", now_utc="2026-10-13T10:30:00Z")
        self.assertEqual(allow["decision"], "ALLOW")
        self.assertEqual(registry.authorize("lease-001", subject="agent:other", action="publish",
            resource="artifact:7", now_utc="2026-10-13T10:30:00Z")["decision"], "DENY")
        self.assertEqual(registry.authorize("lease-001", subject="agent:executor", action="delete",
            resource="artifact:7", now_utc="2026-10-13T10:30:00Z")["decision"], "DENY")
        self.assertEqual(registry.consume("lease-001", subject="agent:executor", action="publish",
            resource="artifact:7", operation_id="op-001", now_utc="2026-10-13T10:30:00Z")["usage_count"], 1)
        self.assertEqual(registry.consume("lease-001", subject="agent:executor", action="attest",
            resource="artifact:8", operation_id="op-002", now_utc="2026-10-13T10:31:00Z")["usage_count"], 2)
        self.assertIn("lease_usage_limit_reached", registry.authorize("lease-001", subject="agent:executor",
            action="publish", resource="artifact:7", now_utc="2026-10-13T10:32:00Z")["reasons"])
        with self.assertRaisesRegex(ValueError, "lease_operation_replay"):
            registry.consume("lease-001", subject="agent:executor", action="publish",
                resource="artifact:7", operation_id="op-001", now_utc="2026-10-13T10:32:00Z")
        registry.revoke("lease-001", actor="root:security", reason="incident",
                        effective_at_utc="2026-10-13T10:33:00Z")
        self.assertIn("lease_revoked", registry.authorize("lease-001", subject="agent:executor",
            action="publish", resource="artifact:7", now_utc="2026-10-13T10:34:00Z")["reasons"])
        view = registry.inspect("lease-001")
        self.assertTrue(view["revoked"])
        self.assertEqual(view["consumption_status"], "CONSUMED")
        self.assertTrue(all(event.get("event_sha256") for event in registry.events))
        with self.assertRaisesRegex(ValueError, "lease_nonce_duplicate"):
            registry.grant(lease_id="lease-002", subject="agent:executor", capability="release.write",
                actions=["publish"], resources=["artifact:7"], nonce="nonce-001", issuer="root:security",
                issued_at_utc="2026-10-13T10:00:00Z", not_before_utc="2026-10-13T10:00:00Z",
                not_after_utc="2026-10-13T11:00:00Z")

    def test_least_privilege_plan_selects_only_goal_ancestors_and_rejects_bad_dags(self):
        dag = {
            "bootstrap": {"depends_on": [], "actions": ["read-manifest"], "resources": ["manifest"]},
            "compile": {"depends_on": ["bootstrap"], "actions": ["compile"], "resources": ["source"]},
            "publish": {"depends_on": ["compile"], "actions": ["publish"], "resources": ["artifact"]},
            "unrelated": {"depends_on": [], "actions": ["delete"], "resources": ["production-db"]},
        }
        plan = auth.derive_least_privilege(dag, goal_nodes=["publish"])
        self.assertEqual(plan["required_nodes"], ["bootstrap", "compile", "publish"])
        self.assertEqual(plan["actions"], ["compile", "publish", "read-manifest"])
        self.assertEqual(plan["resources"], ["artifact", "manifest", "source"])
        self.assertEqual(plan["excluded_nodes"], ["unrelated"])
        self.assertEqual(plan["authority"], "NONE_REQUIRES_CAPABILITY_LEASE")
        self.assertEqual(len(plan["plan_sha256"]), 64)
        with self.assertRaisesRegex(ValueError, "mission_dependency_cycle"):
            auth.derive_least_privilege({
                "a": {"depends_on": ["b"], "actions": [], "resources": []},
                "b": {"depends_on": ["a"], "actions": [], "resources": []},
            }, goal_nodes=["a"])
        with self.assertRaisesRegex(ValueError, "mission_dependency_unknown"):
            auth.derive_least_privilege({
                "a": {"depends_on": ["missing"], "actions": [], "resources": []},
            }, goal_nodes=["a"])
        with self.assertRaisesRegex(ValueError, "mission_goal_unknown"):
            auth.derive_least_privilege(dag, goal_nodes=["missing"])

    def test_time_bound_authority_requires_verified_clock_exact_scope_and_current_interval(self):
        authority = {
            "schema": "SUPER1200_TIME_BOUND_AUTHORITY/1",
            "authority_id": "authority-001", "issuer": "root:security",
            "subject": "agent:executor", "action": "deploy", "object": "release:artifact-7",
            "scope": {"environment": "staging"},
            "not_before_utc": "2026-10-13T10:00:00Z",
            "not_after_utc": "2026-10-13T11:00:00Z",
            "signature": {"algorithm": "TEST-VERIFIER", "value": "authority-signature"},
        }
        authority["authority_sha256"] = hashlib.sha256(auth.canonical_bytes(authority)).hexdigest()
        clock = {
            "schema": "SUPER1200_TRUSTED_CLOCK_ATTESTATION/1",
            "source_id": "clock:trusted-1",
            "observed_at_utc": "2026-10-13T10:30:00Z",
            "expires_at_utc": "2026-10-13T10:31:00Z",
            "max_skew_seconds": 0,
            "signature": {"algorithm": "TEST-VERIFIER", "value": "clock-signature"},
        }
        request = {"subject": "agent:executor", "action": "deploy", "object": "release:artifact-7",
                   "scope": {"environment": "staging"}}
        result = auth.validate_time_bound_authority(
            authority, request=request, now_utc="2026-10-13T10:30:00Z",
            clock_attestation=clock, authority_signature_verifier=lambda *_: True,
            clock_signature_verifier=lambda _: True)
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["trusted_clock_source"], "clock:trusted-1")
        scope_mismatch = dict(request, scope={"environment": "production"})
        denied_scope = auth.validate_time_bound_authority(
            authority, request=scope_mismatch, now_utc="2026-10-13T10:30:00Z",
            clock_attestation=clock, authority_signature_verifier=lambda *_: True,
            clock_signature_verifier=lambda _: True)
        self.assertIn("authority_scope_mismatch", denied_scope["reasons"])
        expired_clock = dict(clock, observed_at_utc="2026-10-13T11:00:00Z", expires_at_utc="2026-10-13T11:01:00Z")
        denied_expiry = auth.validate_time_bound_authority(
            authority, request=request, now_utc="2026-10-13T11:00:00Z",
            clock_attestation=expired_clock, authority_signature_verifier=lambda *_: True,
            clock_signature_verifier=lambda _: True)
        self.assertIn("authority_expired", denied_expiry["reasons"])
        untrusted_clock = auth.validate_time_bound_authority(
            authority, request=request, now_utc="2026-10-13T10:30:00Z",
            clock_attestation=clock, authority_signature_verifier=lambda *_: True,
            clock_signature_verifier=lambda _: False)
        self.assertIn("trusted_clock_signature_invalid", untrusted_clock["reasons"])
        bad_authority_signature = auth.validate_time_bound_authority(
            authority, request=request, now_utc="2026-10-13T10:30:00Z",
            clock_attestation=clock, authority_signature_verifier=lambda *_: False,
            clock_signature_verifier=lambda _: True)
        self.assertIn("authority_signature_invalid", bad_authority_signature["reasons"])


if __name__ == "__main__":
    unittest.main()
