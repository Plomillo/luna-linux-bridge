"""Behavior tests for D04 trust controls, capabilities 117-120."""
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH=Path(__file__).resolve().parents[1]/"domains"/"D04_trust_controls.py"
spec=importlib.util.spec_from_file_location("d04_trust_controls",MODULE_PATH)
trust=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=trust
spec.loader.exec_module(trust)

NOW="2026-10-14T00:20:00Z"


def valid_assignments():
    return {
        "executor":{"actor_id":"actor-a","control_domain":"build","credential_id":"cred-a","execution_path":"runner-a","permissions":["build"],"critical_permissions":["build"],"independence_proof":{"id":"proof-a"}},
        "verifier":{"actor_id":"actor-b","control_domain":"validation","credential_id":"cred-b","execution_path":"runner-b","permissions":["validate"],"critical_permissions":["validate"],"independence_proof":{"id":"proof-b"}},
        "G23":{"actor_id":"actor-c","control_domain":"independent-validation","credential_id":"cred-c","execution_path":"runner-c","permissions":["gate-validate"],"critical_permissions":["gate-validate"],"independence_proof":{"id":"proof-c"}},
        "G24":{"actor_id":"actor-d","control_domain":"independent-certification","credential_id":"cred-d","execution_path":"runner-d","permissions":["gate-certify"],"critical_permissions":["gate-certify"],"independence_proof":{"id":"proof-d"}},
    }


def root(root_id, purpose="super1200-release", key=None, start="2026-01-01T00:00:00Z", end="2027-01-01T00:00:00Z"):
    key=key or "PUBLIC KEY MATERIAL "+root_id
    return {"root_id":root_id,"purpose":purpose,"public_key_material":key,
            "custody_actor":"custodian-"+root_id,"valid_from_utc":start,"valid_until_utc":end,
            "attestation":"custody-attestation-"+root_id}


class D04TrustControlsTests(unittest.TestCase):
    def test_actor_independence_verifier_rejects_shared_identity_domain_credentials_path_and_permissions(self):
        policy={"schema":"SUPER1200_ACTOR_INDEPENDENCE/1",
                "required_roles":["executor","verifier","G23","G24"],
                "required_permissions_by_role":{"executor":["build"],"verifier":["validate"],"G23":["gate-validate"],"G24":["gate-certify"]}}
        assignments=valid_assignments()
        allowed=trust.verify_actor_independence(policy,assignments,
            independence_verifier=lambda role,assignment,declared: bool(assignment.get("independence_proof")) and role in declared["required_roles"])
        self.assertEqual(allowed["decision"],"ALLOW")
        collided={k:dict(v) for k,v in assignments.items()}
        collided["G23"]["actor_id"]="actor-a"
        collided["G24"]["control_domain"]="build"
        collided["verifier"]["credential_id"]="cred-a"
        collided["G24"]["execution_path"]="runner-a"
        collided["G24"]["critical_permissions"]=["build"]
        denied=trust.verify_actor_independence(policy,collided,
            independence_verifier=lambda *_: True)
        self.assertEqual(denied["decision"],"DENY")
        self.assertTrue(any("actor_id_collision" in x for x in denied["reasons"]))
        self.assertTrue(any("control_domain_collision" in x for x in denied["reasons"]))
        self.assertTrue(any("credential_id_collision" in x for x in denied["reasons"]))
        self.assertTrue(any("execution_path_collision" in x for x in denied["reasons"]))
        self.assertTrue(any("critical_permission_collision" in x for x in denied["reasons"]))
        bad_proof=trust.verify_actor_independence(policy,assignments,
            independence_verifier=lambda role,*_: role!="G24")
        self.assertEqual(bad_proof["decision"],"DENY")
        with self.assertRaisesRegex(ValueError,"actor_independence_policy_schema_invalid"):
            trust.verify_actor_independence({"schema":"wrong"},assignments,independence_verifier=lambda *_: True)

    def test_trust_root_registry_binds_key_purpose_custody_validity_and_revocation(self):
        registry=trust.TrustRootRegistry()
        verifier=lambda record: record["public_key_sha256"]==trust.sha256_text(record["public_key_material"],"key")
        registered=registry.register(root("root-a"),attestation_verifier=verifier)
        self.assertEqual(registered["attestation_status"],"VERIFIED_BY_TRUSTED_CALLBACK")
        self.assertEqual(registry.resolve("root-a",purpose="super1200-release",now_utc=NOW)["root_id"],"root-a")
        with self.assertRaisesRegex(ValueError,"trust_root_purpose_mismatch"):
            registry.resolve("root-a",purpose="code-signing",now_utc=NOW)
        with self.assertRaisesRegex(ValueError,"trust_root_identity_immutable"):
            registry.register(root("root-a",key="different key"),attestation_verifier=verifier)
        with self.assertRaisesRegex(ValueError,"trust_root_attestation_verification_failed"):
            registry.register(root("root-b"),attestation_verifier=lambda *_: False)
        registry.revoke("root-a",revocation_id="revoke-a",actor="security-custodian",
            reason="custody breach",effective_at_utc=NOW,
            revocation_verifier=lambda registered,event: registered["root_id"]==event["root_id"] and bool(event["reason"]))
        with self.assertRaisesRegex(ValueError,"trust_root_revoked"):
            registry.resolve("root-a",purpose="super1200-release",now_utc=NOW)
        self.assertTrue(trust.TrustRootRegistry.verify_events(registry.events))
        tampered=list(registry.events)
        tampered[0]["payload"]["root_id"]="replaced"
        self.assertFalse(trust.TrustRootRegistry.verify_events(tampered))

    def test_trust_root_rotation_requires_cross_signatures_overlap_and_monotonic_history(self):
        registry=trust.TrustRootRegistry()
        verifier=lambda record: record["public_key_sha256"]==trust.sha256_text(record["public_key_material"],"key")
        old=registry.register(root("old-root",end="2027-01-01T00:00:00Z"),attestation_verifier=verifier)
        new=registry.register(root("new-root",start="2026-10-01T00:00:00Z",end="2027-10-01T00:00:00Z"),attestation_verifier=verifier)
        rotation=trust.TrustRootRotationLog(registry)
        entry=rotation.rotate("old-root","new-root",now_utc=NOW,overlap_seconds=3600,
            sequence=1,expected_sequence=1,old_root_signature="old-sig",new_root_signature="new-sig",
            old_signature_verifier=lambda o,n,p,s:o["root_id"]=="old-root" and n["root_id"]=="new-root" and s=="old-sig",
            new_signature_verifier=lambda n,o,p,s:n["root_id"]=="new-root" and o["root_id"]=="old-root" and s=="new-sig")
        self.assertEqual(entry["sequence"],1)
        self.assertTrue(entry["cross_signatures_verified"])
        self.assertTrue(trust.TrustRootRotationLog.verify_history(rotation.entries))
        with self.assertRaisesRegex(ValueError,"trust_rotation_sequence_rollback_or_gap"):
            rotation.rotate("new-root","old-root",now_utc=NOW,overlap_seconds=3600,sequence=1,expected_sequence=1,
                old_root_signature="x",new_root_signature="y",old_signature_verifier=lambda *_:True,new_signature_verifier=lambda *_:True)
        with self.assertRaisesRegex(ValueError,"trust_rotation_old_root_signature_verification_failed"):
            trust.TrustRootRotationLog(registry).rotate("old-root","new-root",now_utc=NOW,overlap_seconds=3600,
                sequence=1,expected_sequence=1,old_root_signature="bad",new_root_signature="new-sig",
                old_signature_verifier=lambda *_:False,new_signature_verifier=lambda *_:True)
        bad_overlap_registry=trust.TrustRootRegistry()
        bad_overlap_registry.register(root("short-old",end="2026-10-14T00:21:00Z"),attestation_verifier=verifier)
        bad_overlap_registry.register(root("new-long",start="2026-10-01T00:00:00Z",end="2028-10-01T00:00:00Z"),attestation_verifier=verifier)
        with self.assertRaisesRegex(ValueError,"trust_rotation_old_root_overlap_too_short"):
            trust.TrustRootRotationLog(bad_overlap_registry).rotate("short-old","new-long",now_utc=NOW,overlap_seconds=3600,
                sequence=1,expected_sequence=1,old_root_signature="ok",new_root_signature="ok",
                old_signature_verifier=lambda *_:True,new_signature_verifier=lambda *_:True)
        tampered=list(rotation.entries); tampered[0]["new_root_id"]="attacker-root"
        self.assertFalse(trust.TrustRootRotationLog.verify_history(tampered))

    def test_offline_trust_bundle_binds_version_chain_expiry_hash_and_signature(self):
        bundle=trust.build_offline_trust_bundle(version=1,
            roots=[{"root_id":"root-a","public_key_sha256":"a"*64,"purpose":"release"}],
            intermediates=[{"id":"intermediate-1","sha256":"b"*64}],
            revocations=[{"root_id":"root-z","revoked":True}],
            checkpoints=[{"log":"rekor","size":42,"root_hash":"c"*64}],
            created_at_utc="2026-10-14T00:00:00Z",expires_at_utc="2026-10-15T00:00:00Z",
            previous_bundle_sha256=None,bundle_signature="signed-bundle")
        verified=trust.verify_offline_trust_bundle(bundle,now_utc=NOW,minimum_version=1,
            expected_previous_bundle_sha256=None,bundle_signature_verifier=lambda b:b["bundle_signature"]=="signed-bundle")
        self.assertEqual(verified["decision"],"ALLOW")
        self.assertEqual(verified["root_count"],1)
        self.assertEqual(len(bundle["bundle_sha256"]),64)
        with self.assertRaisesRegex(ValueError,"offline_bundle_rollback_detected"):
            trust.verify_offline_trust_bundle(bundle,now_utc=NOW,minimum_version=2,
                expected_previous_bundle_sha256=None,bundle_signature_verifier=lambda *_:True)
        with self.assertRaisesRegex(ValueError,"offline_bundle_expired"):
            trust.verify_offline_trust_bundle(bundle,now_utc="2026-10-15T00:00:00Z",minimum_version=1,
                expected_previous_bundle_sha256=None,bundle_signature_verifier=lambda *_:True)
        with self.assertRaisesRegex(ValueError,"offline_bundle_chain_mismatch"):
            trust.verify_offline_trust_bundle(bundle,now_utc=NOW,minimum_version=1,
                expected_previous_bundle_sha256="d"*64,bundle_signature_verifier=lambda *_:True)
        tampered=dict(bundle,roots=[{"root_id":"attacker","public_key_sha256":"a"*64}])
        with self.assertRaisesRegex(ValueError,"offline_bundle_content_hash_mismatch"):
            trust.verify_offline_trust_bundle(tampered,now_utc=NOW,minimum_version=1,
                expected_previous_bundle_sha256=None,bundle_signature_verifier=lambda *_:True)
        with self.assertRaisesRegex(ValueError,"offline_bundle_signature_verification_failed"):
            trust.verify_offline_trust_bundle(bundle,now_utc=NOW,minimum_version=1,
                expected_previous_bundle_sha256=None,bundle_signature_verifier=lambda *_:False)


if __name__=="__main__":
    unittest.main()
