from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "implementation/super1200"))
from domains import D04_authority as auth


KEY = b"louksna-test-signing-key-material-32-bytes-minimum"
START = "2026-10-13T00:00:00Z"
END = "2026-10-14T00:00:00Z"
PROVENANCE = {"source": "ci://super1200", "evidence_sha256": "a" * 64,
              "recorded_at_utc": "2026-10-13T12:00:00Z"}


class D04AuthorityTests(unittest.TestCase):
    def test_authorization_proof_binds_subject_action_object_scope_time_and_provenance(self):
        proof = auth.make_authorization_proof(
            subject="runner-7", action="deploy", object_id="service/api", scope=["prod"],
            not_before_utc=START, not_after_utc=END, issuer="runner-7",
            delegation_chain=[], revocation_id="rev-001", provenance=PROVENANCE,
            key_id="key-test-01", signing_key=KEY)
        result = auth.verify_authorization_proof(
            proof, signing_key=KEY, trusted_now_utc="2026-10-13T12:00:00Z",
            expected_subject="runner-7", expected_action="deploy", expected_object_id="service/api",
            required_scope=["prod"], trusted_issuers=["runner-7"], revoked_ids=[])
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["reasons"], [])
        wrong = auth.verify_authorization_proof(
            proof, signing_key=KEY, trusted_now_utc="2026-10-13T12:00:00Z",
            expected_subject="runner-7", expected_action="delete", expected_object_id="service/api",
            required_scope=["prod"], trusted_issuers=["runner-7"], revoked_ids=[])
        self.assertEqual(wrong["decision"], "DENY")
        self.assertIn("authority_action_mismatch", wrong["reasons"])
        revoked = auth.verify_authorization_proof(
            proof, signing_key=KEY, trusted_now_utc="2026-10-13T12:00:00Z",
            expected_subject="runner-7", expected_action="deploy", expected_object_id="service/api",
            required_scope=["prod"], trusted_issuers=["runner-7"], revoked_ids=["rev-001"])
        self.assertIn("authority_revoked", revoked["reasons"])
        tampered = dict(proof, scope=["admin"])
        self.assertIn("authorization_proof_signature_invalid",
                      auth.verify_authorization_proof(tampered, signing_key=KEY,
                        trusted_now_utc="2026-10-13T12:00:00Z", expected_subject="runner-7",
                        expected_action="deploy", expected_object_id="service/api",
                        required_scope=["admin"], trusted_issuers=["runner-7"], revoked_ids=[])["reasons"])

    def test_authorization_proof_requires_contiguous_delegation_and_scope_subset(self):
        chain = [{"from": "root", "to": "operator", "scope": ["prod"],
                  "not_before_utc": START, "not_after_utc": END, "revocation_id": "del-1",
                  "provenance_sha256": "b" * 64},
                 {"from": "operator", "to": "runner", "scope": ["prod"],
                  "not_before_utc": START, "not_after_utc": END, "revocation_id": "del-2",
                  "provenance_sha256": "c" * 64}]
        proof = auth.make_authorization_proof(
            subject="runner", action="release", object_id="artifact-9", scope=["prod"],
            not_before_utc=START, not_after_utc=END, issuer="root",
            delegation_chain=chain, revocation_id="rev-002", provenance=PROVENANCE,
            key_id="key-test-01", signing_key=KEY)
        self.assertEqual(auth.verify_authorization_proof(
            proof, signing_key=KEY, trusted_now_utc="2026-10-13T12:00:00Z",
            expected_subject="runner", expected_action="release", expected_object_id="artifact-9",
            required_scope=["prod"], trusted_issuers=["root"], revoked_ids=[])["decision"], "ALLOW")
        broken = [dict(chain[0]), dict(chain[1], **{"from": "attacker"})]
        with self.assertRaisesRegex(ValueError, "delegation_chain_discontinuous"):
            auth.make_authorization_proof(
                subject="runner", action="release", object_id="artifact-9", scope=["prod"],
                not_before_utc=START, not_after_utc=END, issuer="root", delegation_chain=broken,
                revocation_id="rev-002", provenance=PROVENANCE, key_id="key-test-01", signing_key=KEY)
        with self.assertRaisesRegex(ValueError, "delegation_scope_exceeds_authority"):
            auth.make_authorization_proof(
                subject="runner", action="release", object_id="artifact-9", scope=["prod", "admin"],
                not_before_utc=START, not_after_utc=END, issuer="root", delegation_chain=chain,
                revocation_id="rev-002", provenance=PROVENANCE, key_id="key-test-01", signing_key=KEY)

    def test_capability_lease_is_scoped_expiring_revocable_and_single_consumption(self):
        lease = auth.issue_capability_lease(
            subject="worker-1", actions=["read", "write"], resources=["artifact/a"],
            not_before_utc=START, not_after_utc=END, nonce="nonce-001",
            issuer="policy-authority", lease_id="lease-001", signing_key=KEY)
        first = auth.consume_capability_lease(
            lease, signing_key=KEY, subject="worker-1", action="write", resource="artifact/a",
            trusted_now_utc="2026-10-13T12:00:00Z", revoked_lease_ids=[], consumption_ledger={})
        self.assertEqual(first["decision"], "ALLOW")
        self.assertEqual(first["ledger"], {"lease-001": "nonce-001"})
        replay = auth.consume_capability_lease(
            lease, signing_key=KEY, subject="worker-1", action="write", resource="artifact/a",
            trusted_now_utc="2026-10-13T12:00:00Z", revoked_lease_ids=[], consumption_ledger=first["ledger"])
        self.assertEqual(replay["decision"], "DENY")
        self.assertIn("lease_already_consumed_or_nonce_replayed", replay["reasons"])
        denied = auth.consume_capability_lease(
            lease, signing_key=KEY, subject="worker-1", action="delete", resource="artifact/a",
            trusted_now_utc="2026-10-13T12:00:00Z", revoked_lease_ids=[], consumption_ledger={})
        self.assertEqual(denied["decision"], "DENY")
        self.assertEqual(denied["ledger"], {})
        revoked = auth.consume_capability_lease(
            lease, signing_key=KEY, subject="worker-1", action="write", resource="artifact/a",
            trusted_now_utc="2026-10-13T12:00:00Z", revoked_lease_ids=["lease-001"], consumption_ledger={})
        self.assertIn("lease_revoked", revoked["reasons"])
        expired = auth.consume_capability_lease(
            lease, signing_key=KEY, subject="worker-1", action="write", resource="artifact/a",
            trusted_now_utc="2026-10-14T00:00:00Z", revoked_lease_ids=[], consumption_ledger={})
        self.assertIn("lease_expired", expired["reasons"])

    def test_least_privilege_derives_only_target_dependency_closure(self):
        dag = {"tasks": [
            {"task_id": "fetch", "depends_on": [], "required_actions": ["read"], "required_resources": ["repo/source"]},
            {"task_id": "build", "depends_on": ["fetch"], "required_actions": ["compile"], "required_resources": ["artifact/build"]},
            {"task_id": "debug", "depends_on": [], "required_actions": ["admin"], "required_resources": ["host/root"]},
        ]}
        plan = auth.derive_least_privilege(dag, ["build"])
        self.assertEqual(plan["status"], "PASS")
        self.assertEqual(plan["dependency_closure"], ["build", "fetch"])
        self.assertEqual(plan["minimum_actions"], ["compile", "read"])
        self.assertEqual(plan["minimum_resources"], ["artifact/build", "repo/source"])
        self.assertNotIn("admin", plan["minimum_actions"])
        with self.assertRaisesRegex(ValueError, "mission_dependency_cycle"):
            auth.derive_least_privilege({"tasks": [
                {"task_id": "a", "depends_on": ["b"], "required_actions": ["read"], "required_resources": ["r1"]},
                {"task_id": "b", "depends_on": ["a"], "required_actions": ["write"], "required_resources": ["r2"]}]}, ["a"])
        with self.assertRaisesRegex(ValueError, "mission_dependency_unknown"):
            auth.derive_least_privilege({"tasks": [
                {"task_id": "a", "depends_on": ["missing"], "required_actions": ["read"], "required_resources": ["r1"]}]}, ["a"])

    def test_time_bound_authority_requires_fresh_allowlisted_trusted_time(self):
        authority = auth.make_time_bound_authority(
            authority_id="authority-1", subject="worker-1", actions=["deploy"], resources=["service/api"],
            not_before_utc=START, not_after_utc=END, issuer="root", provenance_sha256="d" * 64)
        trusted = {"schema": "SUPER1200_TRUSTED_TIME/1", "source": "time.service.local",
                   "timestamp_utc": "2026-10-13T12:00:00Z", "observed_at_utc": "2026-10-13T12:00:02Z",
                   "uncertainty_seconds": 1}
        self.assertEqual(auth.evaluate_time_bound_authority(
            authority, trusted_time=trusted, trusted_sources=["time.service.local"])["decision"], "ALLOW")
        early = dict(trusted, timestamp_utc="2026-10-12T23:59:59Z", observed_at_utc="2026-10-12T23:59:59Z")
        self.assertIn("time_authority_not_yet_valid", auth.evaluate_time_bound_authority(
            authority, trusted_time=early, trusted_sources=["time.service.local"])["reasons"])
        stale = dict(trusted, observed_at_utc="2026-10-13T12:10:00Z")
        self.assertIn("trusted_time_observation_stale", auth.evaluate_time_bound_authority(
            authority, trusted_time=stale, trusted_sources=["time.service.local"])["reasons"])
        untrusted = dict(trusted, source="unknown-clock")
        self.assertIn("trusted_time_source_untrusted", auth.evaluate_time_bound_authority(
            authority, trusted_time=untrusted, trusted_sources=["time.service.local"])["reasons"])
        uncertain = dict(trusted, uncertainty_seconds=30)
        self.assertIn("trusted_time_uncertainty_excessive", auth.evaluate_time_bound_authority(
            authority, trusted_time=uncertain, trusted_sources=["time.service.local"])["reasons"])
        tampered = dict(authority, not_after_utc="2026-10-15T00:00:00Z")
        self.assertIn("time_authority_hash_invalid", auth.evaluate_time_bound_authority(
            tampered, trusted_time=trusted, trusted_sources=["time.service.local"])["reasons"])


if __name__ == "__main__":
    unittest.main()
