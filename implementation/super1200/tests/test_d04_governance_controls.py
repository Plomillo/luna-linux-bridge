import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "implementation/super1200/domains/D04_governance_controls.py"
spec = importlib.util.spec_from_file_location("d04_governance_controls_tests", MODULE_PATH)
controls = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = controls
spec.loader.exec_module(controls)


def one_time_proof(proof_id="proof-once", nonce="nonce-once"):
    proof = {
        "schema": "SUPER1200_SINGLE_USE_AUTHORIZATION/1",
        "proof_id": proof_id,
        "nonce": nonce,
        "subject": "agent:publisher",
        "action": "publish",
        "object": "artifact:42",
        "scope": {"environment": "staging"},
        "issuer": "root:security",
        "not_before_utc": "2026-10-14T00:00:00Z",
        "not_after_utc": "2026-10-14T01:00:00Z",
        "signature": {"algorithm": "TEST", "value": "signed-proof"},
    }
    unsigned = dict(proof)
    unsigned.pop("proof_integrity_sha256", None)
    proof["proof_integrity_sha256"] = hashlib.sha256(controls.canonical_bytes(unsigned)).hexdigest()
    return proof


def approval(request, *, approval_id, actor, credential, domain, risk="critical-release",
             issued="2026-10-14T00:10:00Z", expires="2026-10-14T00:20:00Z"):
    result = {
        "schema": "SUPER1200_TWO_MAN_APPROVAL/1",
        "approval_id": approval_id,
        "actor_id": actor,
        "credential_id": credential,
        "control_domain": domain,
        "risk": risk,
        "request_sha256": hashlib.sha256(controls.canonical_bytes(request)).hexdigest(),
        "issued_at_utc": issued,
        "expires_at_utc": expires,
        "signature": {"algorithm": "TEST", "value": "signature-" + approval_id},
    }
    unsigned = dict(result)
    unsigned.pop("signature", None)
    unsigned.pop("approval_sha256", None)
    result["approval_sha256"] = hashlib.sha256(controls.canonical_bytes(unsigned)).hexdigest()
    return result


class D04GovernanceControlsTests(unittest.TestCase):
    def test_single_use_authorization_is_atomic_and_replay_is_denied(self):
        registry = controls.SingleUseAuthorizationRegistry()
        proof = one_time_proof()
        request = {"subject": "agent:publisher", "action": "publish",
                   "object": "artifact:42", "scope": {"environment": "staging"}}
        verifier = lambda p, req, now: (
            p["subject"] == req["subject"] and p["action"] == req["action"]
            and p["object"] == req["object"] and p["scope"] == req["scope"]
            and "2026-10-14T00:00:00" <= now < "2026-10-14T01:00:00"
            and p["signature"]["value"] == "signed-proof"
        )
        receipt = registry.consume(proof, request=request, operation_id="op-1",
                                   now_utc="2026-10-14T00:15:00Z", proof_verifier=verifier)
        self.assertEqual(receipt["schema"], "SUPER1200_SINGLE_USE_RECEIPT/1")
        self.assertEqual(receipt["sequence"], 1)
        self.assertTrue(controls.SingleUseAuthorizationRegistry.verify_receipts(registry.receipts))
        with self.assertRaisesRegex(ValueError, "single_use_proof_replay"):
            registry.consume(proof, request=request, operation_id="op-2",
                             now_utc="2026-10-14T00:16:00Z", proof_verifier=verifier)
        with self.assertRaisesRegex(ValueError, "single_use_proof_not_authorized"):
            registry.consume(one_time_proof("proof-2", "nonce-2"), request=request,
                             operation_id="op-3", now_utc="2026-10-14T00:15:00Z",
                             proof_verifier=lambda *_: False)
        tampered = one_time_proof("proof-3", "nonce-3")
        tampered["action"] = "delete"
        with self.assertRaisesRegex(ValueError, "single_use_proof_integrity_mismatch"):
            registry.consume(tampered, request=request, operation_id="op-4",
                             now_utc="2026-10-14T00:15:00Z", proof_verifier=lambda *_: True)

    def test_revocation_registry_propagates_and_unknown_tracking_fails_closed(self):
        registry = controls.RevocationRegistry()
        registry.track(subject_id="root-proof", issuer="root:security", registry_checkpoint="checkpoint-1")
        registry.track(subject_id="derived-lease", issuer="root:security", registry_checkpoint="checkpoint-1")
        registry.track(subject_id="session", issuer="root:security", registry_checkpoint="checkpoint-1")
        registry.add_dependent(issuer="root:security", source_subject_id="root-proof",
                               dependent_subject_id="derived-lease")
        registry.add_dependent(issuer="root:security", source_subject_id="derived-lease",
                               dependent_subject_id="session")
        self.assertEqual(registry.check(subject_id="session", issuer="root:security",
            now_utc="2026-10-14T00:05:00Z")["status"], "NOT_REVOKED")
        revoked = registry.revoke(subject_id="root-proof", issuer="root:security",
            revocation_id="rev-001", actor="root:security", reason="credential compromise",
            effective_at_utc="2026-10-14T00:10:00Z")
        self.assertEqual(revoked["propagation_count"], 3)
        check = registry.check(subject_id="session", issuer="root:security",
            now_utc="2026-10-14T00:10:00Z")
        self.assertEqual(check["status"], "REVOKED")
        self.assertEqual(check["decision"], "DENY")
        unknown = registry.check(subject_id="untracked", issuer="root:security",
            now_utc="2026-10-14T00:11:00Z")
        self.assertEqual(unknown["status"], "UNKNOWN")
        self.assertEqual(unknown["decision"], "DENY")
        with self.assertRaisesRegex(ValueError, "revocation_record_immutable"):
            registry.revoke(subject_id="root-proof", issuer="root:security",
                revocation_id="rev-002", actor="root:security", reason="different",
                effective_at_utc="2026-10-14T00:12:00Z")
        self.assertTrue(all(event.get("event_sha256") for event in registry.events))

    def test_separation_of_duties_rejects_shared_identity_control_domain_and_permissions(self):
        roles = ["executor", "verifier", "G23", "G24"]
        policy = {
            "schema": "SUPER1200_SEPARATION_OF_DUTIES/1",
            "required_roles": roles,
            "allowed_permissions_by_role": {
                "executor": ["build", "write-evidence"],
                "verifier": ["read-source", "run-tests"],
                "G23": ["validate-evidence"],
                "G24": ["certify-scope"],
            },
        }
        assignments = {
            "executor": {"actor_id":"actor-A","control_domain":"build-system","credential_id":"cred-A","execution_path":"runner-A",
                         "permissions":["build","write-evidence"],"critical_permissions":["write-evidence"]},
            "verifier": {"actor_id":"actor-B","control_domain":"validation-system","credential_id":"cred-B","execution_path":"runner-B",
                         "permissions":["read-source","run-tests"],"critical_permissions":["run-tests"]},
            "G23": {"actor_id":"actor-C","control_domain":"validation-authority","credential_id":"cred-C","execution_path":"runner-C",
                    "permissions":["validate-evidence"],"critical_permissions":["validate-evidence"]},
            "G24": {"actor_id":"actor-D","control_domain":"certification-authority","credential_id":"cred-D","execution_path":"runner-D",
                    "permissions":["certify-scope"],"critical_permissions":["certify-scope"]},
        }
        self.assertEqual(controls.validate_separation_of_duties(policy, assignments)["decision"], "ALLOW")
        collided = {k: dict(v) for k, v in assignments.items()}
        collided["G23"]["actor_id"] = "actor-A"
        collided["G24"]["permissions"] = ["certify-scope", "write-evidence"]
        denied = controls.validate_separation_of_duties(policy, collided)
        self.assertEqual(denied["decision"], "DENY")
        self.assertTrue(any("actor_id_collision" in r for r in denied["reasons"]))
        self.assertTrue(any("role_excess_permissions:G24" in r for r in denied["reasons"]))
        missing = {k: dict(v) for k, v in assignments.items()}
        del missing["G24"]
        self.assertTrue(any("role_assignment_missing:G24" in r for r in controls.validate_separation_of_duties(policy, missing)["reasons"]))

    def test_two_man_rule_requires_configured_threshold_independent_signed_fresh_approvals(self):
        policy = {
            "schema": "SUPER1200_TWO_MAN_RULE/1",
            "risk_thresholds": {"critical-release": 2, "trust-root-rotation": 3},
            "default_threshold": 1,
            "max_approval_age_seconds": 600,
        }
        request = {"action": "publish", "artifact_sha256": "a" * 64, "target": "staging"}
        valid_approvals = [
            approval(request, approval_id="approval-1", actor="actor-A", credential="cred-A", domain="security"),
            approval(request, approval_id="approval-2", actor="actor-B", credential="cred-B", domain="platform"),
        ]
        result = controls.evaluate_two_man_rule(policy, risk="critical-release", request=request,
            approvals=valid_approvals, now_utc="2026-10-14T00:15:00Z",
            signature_verifier=lambda item, payload: bool(payload) and item["signature"]["value"].startswith("signature-"),
            independence_verifier=lambda item, req: item["actor_id"] not in {"shared-actor"} and req == request)
        self.assertEqual(result["decision"], "ALLOW")
        self.assertTrue(result["two_man_rule_applied"])
        one = controls.evaluate_two_man_rule(policy, risk="critical-release", request=request,
            approvals=valid_approvals[:1], now_utc="2026-10-14T00:15:00Z",
            signature_verifier=lambda *_: True, independence_verifier=lambda *_: True)
        self.assertEqual(one["decision"], "DENY")
        duplicate = [valid_approvals[0], approval(request, approval_id="approval-3", actor="actor-A",
                    credential="cred-C", domain="independent")]
        collision = controls.evaluate_two_man_rule(policy, risk="critical-release", request=request,
            approvals=duplicate, now_utc="2026-10-14T00:15:00Z",
            signature_verifier=lambda *_: True, independence_verifier=lambda *_: True)
        self.assertEqual(collision["decision"], "DENY")
        stale = [approval(request, approval_id="approval-old", actor="old-A", credential="old-cred",
                          domain="old-domain", issued="2026-10-13T23:00:00Z", expires="2026-10-14T02:00:00Z"),
                 valid_approvals[1]]
        stale_result = controls.evaluate_two_man_rule(policy, risk="critical-release", request=request,
            approvals=stale, now_utc="2026-10-14T00:15:00Z",
            signature_verifier=lambda *_: True, independence_verifier=lambda *_: True)
        self.assertEqual(stale_result["decision"], "DENY")
        low_risk = controls.evaluate_two_man_rule(policy, risk="routine", request=request,
            approvals=valid_approvals[:1], now_utc="2026-10-14T00:15:00Z",
            signature_verifier=lambda *_: True, independence_verifier=lambda *_: True)
        self.assertEqual(low_risk["decision"], "ALLOW")
        self.assertFalse(low_risk["two_man_rule_applied"])


if __name__ == "__main__":
    unittest.main()
