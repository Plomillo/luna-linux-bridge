from __future__ import annotations
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
from custoszv9.crfu.anti_paralysis import decide_next_action, state_fingerprint, retry_decision
from custoszv9.crfu.evidence import append_event, verify_journal
from custoszv9.crfu.event_queue import PersistentMissionQueue
from custoszv9.crfu.formal import validate_proof_bundle
from custoszv9.crfu.gates import CANONICAL_GATES, LOCAL_PUAC_CONTROLS, evaluate_gate_evidence
from custoszv9.crfu.model import sha256_bytes, canonical_json
from custoszv9.crfu.planner import ActionSpec, build_plan
from custoszv9.crfu.recovery import checkpoint_record, verify_restoration
from custoszv9.crfu.resources import ResourceBudget, ResourceSnapshot, evaluate_budget
from custoszv9.crfu.puac2 import (
    classify_claim_conflicts, coverage_report, evaluate_incident_closure,
    transitive_dependency_impact, validate_authority_binding, validate_claim_v2,
    validate_event_records, validate_puac_control, validate_recovery_plan,
    PUAC_CONTROL_OUTPUTS, PUAC_CONTROL_TRUE_FLAGS, PUAC_CONTROL_FALSE_FLAGS
)
GATE_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "custoszv9_gate_trust_root.py"
_GATE_SPEC = importlib.util.spec_from_file_location("custoszv9_gate_trust_root_tests", GATE_SCRIPT_PATH)
assert _GATE_SPEC is not None and _GATE_SPEC.loader is not None
gate_trust_root = importlib.util.module_from_spec(_GATE_SPEC)
_GATE_SPEC.loader.exec_module(gate_trust_root)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

def generate_ed25519_pems():
    key = Ed25519PrivateKey.generate()
    private_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode("ascii")
    public_pem = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("ascii")
    return key, private_pem, public_pem


def valid_puac_payload(control_id, package_sha, commit_sha, producer, evaluator):
    """Construct a syntactically complete local-control record for negative/positive tests."""
    payload = {}
    def value_for(key):
        if key == "scope_evidence": return {"package_sha256": package_sha, "scope": "candidate-software"}
        if key == "evidence_coverage": return {"candidate_sha256": package_sha, "documentary_and_operational_separated": True}
        if key == "allowed_evaluators": return [evaluator]
        if key == "separation_evidence": return {"candidate_sha256": package_sha, "roles_separated": True}
        if key == "evaluator_identity": return evaluator
        if key == "producer_identity": return producer
        if key == "threat_model": return {"candidate_sha256": package_sha, "threats": []}
        if key == "risk_criteria": return {"critical_risk_policy": "DENY"}
        if key == "residual_risk_record": return {"candidate_sha256": package_sha, "residual_risks": []}
        if key == "reproduction_report": return {"status": "PASS", "candidate_sha256": package_sha}
        if key == "artifact_bytes_identity": return {"sha256": package_sha, "size_bytes": 1}
        if key == "dependency_lock": return {"locked": True}
        if key == "build_recipe": return {"identified": True}
        if key == "execution_environment": return {"identified": True}
        if key in ("provenance_attestation", "supply_chain_evidence"): return {"source_commit": commit_sha}
        if key == "candidate_build": return {"package_sha256": package_sha, "commit_sha": commit_sha}
        if key == "dependency_graph": return {"module-a": []}
        if key == "impact_graph": return {"changed": [], "impacted": []}
        if key == "checkpoint":
            return {"sha256": hashlib.sha256(b"checkpoint").hexdigest()}
        if key == "restoration_evidence":
            return {"restoration_proven": True, "checkpoint_sha256": hashlib.sha256(b"checkpoint").hexdigest()}
        if key == "rollback_test": return {"status": "PASS", "candidate_sha256": package_sha}
        if key == "monitoring_profile": return {"responsible_roles": [evaluator], "candidate_sha256": package_sha}
        if key in ("observations", "change_events", "unresolved_claims", "exclusions",
                   "conflict_of_interest_records", "preserved_claims", "invalidated_claims",
                   "previous_evidence", "irreversible_side_effects", "restoration_oracles"):
            return []
        if key in ("claim_registry",): return []
        if key in ("acceptance_criteria",): return ["exact digest is verified"]
        if key in ("risk_register",): return {"candidate_sha256": package_sha, "risks": []}
        if key in ("integrity_report",): return {"candidate_sha256": package_sha}
        if key in ("manifest",): return {"candidate_sha256": package_sha}
        if key in ("actor_registry",): return [producer, evaluator]
        if key in ("role_assignments",): return [{"actor": producer, "role": "producer"}, {"actor": evaluator, "role": "evaluator"}]
        if key in ("evaluation_plan",): return {"steps": ["independent-recheck"]}
        if key in ("previous_baseline",): return {"sha256": "d" * 64}
        if key in ("candidate_build",): return {"package_sha256": package_sha, "commit_sha": commit_sha}
        if key in ("change_set",): return {"files_changed": []}
        if key in ("revalidation_plan",): return ["rerun impacted checks"]
        if key in ("operation_plan",): return {"restore_then_verify": True}
        if key in ("restoration_procedure",): return {"steps": ["restore", "verify"]}
        if key in ("expected_state",): return {"sha256": "e" * 64}
        if key in ("rollback_test",): return {"status": "PASS"}
        if key in ("assurance_status",): return {"status": "monitored"}
        if key in ("impact_assessment",): return {"affected_claims": []}
        if key in ("suspension_recommendation", "revalidation_request", "recertification_request"): return {"status": "none"}
        if key in ("approved_scope",): return {"scope": "candidate-software"}
        if key in ("exclusions",): return []
        if key in ("separation_evidence",): return {"candidate_sha256": package_sha, "roles_separated": True}
        if key in ("threat_assessment",): return {"status": "assessed"}
        if key in ("treatment_plan",): return {"status": "tracked"}
        if key in ("supply_chain_evidence",): return {"candidate_sha256": package_sha}
        if key in ("recovery_limitations",): return []
        if key in ("restoration_tested",): return True
        if key in ("assurance_case",): return {"claims": [], "argument": "fixture"}
        if key in ("argumentation_record",): return {"premises": [], "inferences": []}
        if key in ("evidence_coverage",): return {"candidate_sha256": package_sha}
        if key in ("monitoring_profile",): return {"responsible_roles": [evaluator], "candidate_sha256": package_sha}
        return {}
    for key in PUAC_CONTROL_OUTPUTS[control_id]:
        payload[key] = value_for(key)
    for key in PUAC_CONTROL_TRUE_FLAGS[control_id]:
        payload[key] = True
    for key in PUAC_CONTROL_FALSE_FLAGS[control_id]:
        payload[key] = False
    if control_id == "PUAC.C26":
        payload["unresolved_claims"] = []
        payload["assurance_case"] = {"claims": [], "argument": "fixture"}
        payload["argumentation_record"] = {"premises": [], "inferences": []}
    if control_id == "PUAC.C27":
        payload["evaluator_identity"] = evaluator
        payload["producer_identity"] = producer
        payload["allowed_evaluators"] = [evaluator]
        payload["separation_evidence"] = {"candidate_sha256": package_sha}
    if control_id == "PUAC.C29":
        payload["artifact_bytes_identity"] = {"sha256": package_sha, "size_bytes": 1}
        payload["reproduction_report"] = {"status": "PASS"}
    if control_id == "PUAC.C30":
        payload["candidate_build"] = {"package_sha256": package_sha, "commit_sha": commit_sha}
        payload["dependency_graph"] = {"module-a": []}
        payload["impact_graph"] = {"changed": [], "impacted": []}
    if control_id == "PUAC.C31":
        cp = hashlib.sha256(b"checkpoint").hexdigest()
        payload["checkpoint"] = {"sha256": cp}
        payload["restoration_evidence"] = {"restoration_proven": True, "checkpoint_sha256": cp}
        payload["rollback_test"] = {"status": "PASS"}
    if control_id == "PUAC.C32":
        payload["monitoring_profile"] = {"responsible_roles": [evaluator]}
        payload["observations"] = []
        payload["change_events"] = []
    unsigned_digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    payload["evidence_binding"] = {
        "schema": "PUAC2_CONTROL_EVIDENCE_BINDING/1.0",
        "control_id": control_id,
        "candidate_sha256": package_sha,
        "candidate_commit_sha": commit_sha,
        "payload_sha256": unsigned_digest,
        "producer_identity": producer,
        "evaluator_identity": evaluator,
        "generated_at_utc": "2026-10-16T22:00:00Z",
        "scope": "candidate-software",
        "source_evidence_refs": [{"uri": "evidence://test-fixture", "sha256": "f" * 64}]
    }
    return payload


class CRFUTests(unittest.TestCase):
    def test_deterministic_dependency_order_and_no_authorization(self):
        out=build_plan([ActionSpec("c",("b",)),ActionSpec("a"),ActionSpec("b",("a",))],
          max_alternatives=5,available_capabilities=set(),admissible_effects=set())
        self.assertEqual(out["ordered_actions"],["a","b","c"])
        self.assertFalse(out["execution_authorized"])
    def test_dependency_cycle_denied(self):
        out=build_plan([ActionSpec("a",("b",)),ActionSpec("b",("a",))],
          max_alternatives=4,available_capabilities=set(),admissible_effects=set())
        self.assertEqual(out["reason"],"DEPENDENCY_CYCLE")
    def test_unresolved_dependency_holds(self):
        out=build_plan([ActionSpec("a",("missing",))],max_alternatives=4,available_capabilities=set(),admissible_effects=set())
        self.assertEqual(out["status"],"HOLD")
    def test_unknown_resources_hold(self):
        out=evaluate_budget(ResourceBudget(1,1,1,1),ResourceSnapshot(None,None,None,"2026-01-01T00:00:00Z","test","UNKNOWN"))
        self.assertEqual(out["status"],"HOLD")
    def _measured_snapshot(self, ram: int, disk: int, cpu: int = 4) -> ResourceSnapshot:
        return ResourceSnapshot(ram, disk, cpu, "2026-10-17T00:00:00Z", "test-fixture", "MEASURED")

    def test_ram_strict_boundary_equality_fails(self):
        result = evaluate_budget(
            ResourceBudget(900, 100, 10, 1),
            self._measured_snapshot(1000, 2000),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("RAM_BUDGET_EXCEEDED", result["reasons"])

    def test_ram_one_byte_inside_strict_boundary_passes(self):
        result = evaluate_budget(
            ResourceBudget(899, 100, 10, 1),
            self._measured_snapshot(1000, 2000),
        )
        self.assertEqual(result["status"], "PASS")

    def test_ram_reservation_above_available_fails_even_for_zero_demand(self):
        result = evaluate_budget(
            ResourceBudget(0, 101, 10, 1),
            self._measured_snapshot(100, 2000),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("RAM_BUDGET_EXCEEDED", result["reasons"])

    def test_ram_reservation_equal_to_available_fails_even_for_zero_demand(self):
        result = evaluate_budget(
            ResourceBudget(0, 100, 10, 1),
            self._measured_snapshot(100, 2000),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("RAM_BUDGET_EXCEEDED", result["reasons"])

    def test_disk_strict_boundary_equality_fails(self):
        result = evaluate_budget(
            ResourceBudget(10, 10, 2000, 1),
            self._measured_snapshot(1000, 2000),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("DISK_BUDGET_EXCEEDED", result["reasons"])

    def test_disk_one_byte_inside_strict_boundary_passes(self):
        result = evaluate_budget(
            ResourceBudget(10, 10, 1999, 1),
            self._measured_snapshot(1000, 2000),
        )
        self.assertEqual(result["status"], "PASS")

    def test_invalid_numeric_measurement_holds_instead_of_raising_or_passing(self):
        snapshot = ResourceSnapshot(True, 2000, 4, "2026-10-17T00:00:00Z", "test-fixture", "MEASURED")
        result = evaluate_budget(ResourceBudget(0, 0, 0, 1), snapshot)
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("RESOURCE_MEASUREMENT_INVALID:ram_available_bytes", result["reasons"])

    def test_repeated_strategy_without_evidence_blocked(self):
        h=state_fingerprint({"revision":1})
        out=decide_next_action(action_id="a",strategy_id="s",state_hash=h,
          previous_attempts=[{"action_id":"a","strategy_id":"s","state_hash":h}],new_evidence=False,
          planning_budget_remaining=1,retry_budget_remaining=0)
        self.assertEqual(out["reason"],"REPEATED_STRATEGY_WITHOUT_NEW_EVIDENCE")
    def test_retry_is_finite_and_idempotency_aware(self):
        unknown=retry_decision(idempotency_class="UNKNOWN",retries_used=0,max_retries=2,
            transient_failure=True,authorization_valid=True)
        self.assertEqual(unknown["decision"],"DENY_RETRY")
        unsafe=retry_decision(idempotency_class="NON_IDEMPOTENT",retries_used=0,max_retries=2,
            transient_failure=True,authorization_valid=True,idempotency_key=None,effects_reconciled=False)
        self.assertEqual(unsafe["decision"],"DENY_RETRY")
        safe=retry_decision(idempotency_class="IDEMPOTENT",retries_used=0,max_retries=1,
            transient_failure=True,authorization_valid=True,wait_seconds=5)
        self.assertEqual(safe["decision"],"WAIT_CONDITIONALLY")
        exhausted=retry_decision(idempotency_class="IDEMPOTENT",retries_used=1,max_retries=1,
            transient_failure=True,authorization_valid=True)
        self.assertEqual(exhausted["reason"],"RETRY_BUDGET_EXHAUSTED")
    def test_wait_requires_deadline(self):
        h="a"*64
        out=decide_next_action(action_id="a",strategy_id="s",state_hash=h,previous_attempts=[],new_evidence=False,
          planning_budget_remaining=1,retry_budget_remaining=0,wait_condition="host online")
        self.assertEqual(out["reason"],"UNBOUNDED_WAIT_FORBIDDEN")
    def test_journal_chain_and_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"journal.jsonl"
            event={"operation_id":"op","mission_id":"m","sequence_id":1,"timestamp_utc":"2026-01-01T00:00:00Z",
              "actor":"test","tool_and_version":"test/1","source_identity":"s",
              "input_hash_and_size":{"sha256":sha256_bytes(b"i"),"size_bytes":1},
              "output_hash_and_size":{"sha256":sha256_bytes(b"o"),"size_bytes":1},
              "validation_result":"PASS","authorization_evidence_reference":"test-only",
              "dependency_context":[],"rollback_pointer":None,"status":"TEST_ONLY"}
            append_event(path,event)
            self.assertEqual(verify_journal(path)["status"],"PASS")
            path.write_text(path.read_text().replace('"status":"TEST_ONLY"','"status":"TAMPERED"'),encoding="utf-8")
            self.assertEqual(verify_journal(path)["status"],"FAIL")
    def test_formal_bundle_wrong_digest_holds(self):
        target=hashlib.sha256(b"target").hexdigest()
        good={"target_sha256":target,"scope":"unit-test","specification_sha256":hashlib.sha256(b"spec").hexdigest(),
          "toolchain":{"name":"Agda","version":"pinned"},"assumptions":[],"limitations":[],
          "status":"PASS","evidence_verified":True,"transportable_properties":["dependency_safety"]}
        self.assertEqual(validate_proof_bundle(good,"0"*64,"unit-test")["status"],"HOLD")
    def test_gates_missing_evidence_hold(self):
        out=evaluate_gate_evidence([],candidate_commit_sha="a"*40,package_sha256="b"*64,
           trusted_workflow_sha="c"*40,producer_identity="producer")
        self.assertEqual(out["status"],"HOLD")
        self.assertFalse(out["release_eligible"])
        self.assertEqual(len(CANONICAL_GATES),24)
        self.assertEqual(len(LOCAL_PUAC_CONTROLS),8)
    def test_event_queue_resumes_only_on_matching_signal_and_verifies_chain(self):
        task={
          "task_id":"task-event","mission_id":"task-event","project_id":"p","source_identity":"s",
          "target_identity":"t","source_state_hash":"a"*64,"dependency_set":[],
          "authorized_scope":"read-only","required_capabilities":[],"inputs":[],"preconditions":[],
          "permitted_effects":[],"resource_budget":{"ram_required_bytes":0,"ram_reserved_bytes":0,
          "disk_required_bytes":0,"max_concurrency":1},"execution_deadline":"2099-01-01T00:00:00Z",
          "maximum_planning_budget":3,"maximum_retry_budget":0,"acceptance_criteria":["valid"],
          "expected_outputs":[],"validation_strategy":"hash","evidence_requirements":["journal"],
          "checkpoint_reference":None,"rollback_strategy":"none","completion_condition":"done",
          "escalation_condition":"blocked","authorization_evidence_reference":"test-reference"}
        with tempfile.TemporaryDirectory() as td:
            q=PersistentMissionQueue(Path(td)/"queue.sqlite")
            self.assertEqual(q.submit(task)["state"],"RECEIVED")
            self.assertEqual(q.transition("task-event","RECEIVED","PREFLIGHT",event_type="PREFLIGHT")["state"],"PREFLIGHT")
            self.assertEqual(q.transition("task-event","PREFLIGHT","READY",event_type="PLAN_VALID")["state"],"READY")
            self.assertEqual(q.claim_next_ready()["state"],"RUNNING")
            with self.assertRaises(ValueError):
                q.transition("task-event","RUNNING","WAITING_FOR_EVENT",event_type="WAIT",fields={"wait_condition":"host"})
            q.transition("task-event","RUNNING","WAITING_FOR_EVENT",event_type="WAIT",
                fields={"wait_condition":"host-online","wait_deadline_utc":"2099-01-01T00:00:00Z"})
            self.assertEqual(q.emit_signal("unrelated")["resumed"],[])
            self.assertEqual(q.get("task-event")["state"],"WAITING_FOR_EVENT")
            self.assertEqual(q.emit_signal("host-online")["resumed"],["task-event"])
            self.assertEqual(q.get("task-event")["state"],"READY")
            self.assertEqual(q.verify_event_chain()["status"],"PASS")
    def test_typed_claim_units_and_semantic_key_conflicts(self):
        base={"claim_id":"claim-1","subject_id":"system","property_id":"ram","scope_id":"build",
          "context_id":"linux-runner","version":"1","validity_interval":{"not_before_utc":"2000-01-01T00:00:00Z","expires_at_utc":"2099-01-01T00:00:00Z"},
          "unit_of_measure":{"unit_id":"byte","dimension":"information","version":"1"},"value":100,"evidence_state":"SUPPORTED"}
        self.assertEqual(validate_claim_v2(base)["status"],"PASS_SCHEMA_ONLY")
        other=dict(base);other["claim_id"]="claim-2";other["value"]=200
        result=classify_claim_conflicts([base,other])
        self.assertEqual(result["status"],"CONFLICT")
        bad=dict(base);bad["unit_of_measure"]={"unit_id":"kilogram"}
        self.assertEqual(validate_claim_v2(bad)["status"],"HOLD")
    def test_event_records_require_recorded_time_and_acyclic_causality(self):
        event=lambda event_id,seq,parents:{"event_id":event_id,"event_time_utc":"2026-10-16T10:00:00Z",
            "observed_at_utc":"2026-10-16T10:01:00Z","recorded_at_utc":"2026-10-16T10:02:00Z",
            "sequence_number":seq,"causal_parents":parents}
        valid=validate_event_records([event("a",1,[]),event("b",2,[])])
        self.assertEqual(valid["status"],"PASS")
        cycle=validate_event_records([event("a",1,["b"]),event("b",2,["a"])])
        self.assertEqual(cycle["status"],"FAIL")
    def test_authority_binding_needs_trusted_scope_verifier(self):
        binding={"binding_id":"b1","actor_id":"agent","actor_identity_proof":"proof-a","role_id":"executor",
          "issuer_id":"issuer","issuer_authority_proof":"proof-i","action":"write","object_id":"repo",
          "scope_id":"feature-branch","validity_interval":{"not_before_utc":"2000-01-01T00:00:00Z","expires_at_utc":"2099-01-01T00:00:00Z"},
          "delegation_chain":[],"revocation_state":"NOT_REVOKED","provenance_id":"prov"}
        denied=validate_authority_binding(binding,action="write",object_id="repo",scope_id="feature-branch",trust_verifier=None)
        self.assertEqual(denied["status"],"DENY")
        passed=validate_authority_binding(binding,action="write",object_id="repo",scope_id="feature-branch",
          trust_verifier=lambda b:{"status":"PASS","binding_id":b["binding_id"],"actor_identity_verified":True,"issuer_authority_verified":True,"delegation_chain_verified":True,"revocation_checked":True,"validity_checked":True,"action_scope_verified":True,"least_privilege_verified":True})
        self.assertEqual(passed["status"],"PASS")
        self.assertEqual(validate_authority_binding(binding,action="delete",object_id="repo",scope_id="feature-branch",
          trust_verifier=lambda b:{"status":"PASS","binding_id":b["binding_id"],"actor_identity_verified":True,"issuer_authority_verified":True,"delegation_chain_verified":True,"revocation_checked":True,"validity_checked":True,"action_scope_verified":True,"least_privilege_verified":True})["status"],"DENY")
    def test_recovery_plan_does_not_claim_restoration_or_activation(self):
        plan={"incident_id":"i1","authorized_actor":"actor","checkpoint_id":"cp",
          "checkpoint_hash":sha256_bytes(b"snapshot"),"target_environment":"test-host","dependency_hashes":[sha256_bytes(b"dep")],
          "restoration_oracles":["state-hash"],"nonregression_plan":"run checks","rollback_scope":"local",
          "irreversible_side_effects":[],"authority_ref":"binding"}
        self.assertEqual(validate_recovery_plan(plan)["status"],"PASS_SCHEMA_ONLY")
        evidence={"diagnosis_verified":True,"correction_authorized":True,"correction_executed":True,
          "restoration_verified":True,"nonregression_verified":True,"traceability_complete":True,
          "g23_g24_required":True,"g23_g24_pass":True,"new_operational_authorization":True}
        closed=evaluate_incident_closure(evidence)
        self.assertTrue(closed["incident_closed"])
        self.assertFalse(closed["activation_authorized"])
    def test_coverage_keeps_documentary_and_operational_counts_separate(self):
        digest="a"*64
        report=coverage_report([{"requirement_id":"R1"},{"requirement_id":"R2"}],["R1"],
          [{"requirement_id":"R1","status":"PASS","reference_only":True,"target_sha256":digest},
           {"requirement_id":"R2","status":"PASS","target_sha256":digest},
           {"record_type":"TEST_CLASS","test_class_id":"T01","status":"PASS","target_sha256":digest},
           {"record_type":"INVARIANT","invariant_id":"INV-01","status":"PASS","target_sha256":digest}],
          target_sha256=digest)
        self.assertEqual(report["documentation"]["covered"],1)
        self.assertEqual(report["operational"]["covered"],1)
        self.assertEqual(report["T_operational"]["passed"],1)
        self.assertEqual(report["I_operational"]["proven"],1)
        self.assertIsNone(coverage_report([],[],[])["operational_coverage"])
    def test_transitive_impact_closure_and_cycles(self):
        graph={"A":[],"B":["A"],"C":["B"],"D":[]}
        out=transitive_dependency_impact(graph,["A"])
        self.assertEqual(out["impacted_nodes"],["B","C"])
        self.assertEqual(transitive_dependency_impact({"A":["B"],"B":["A"]},["A"])["status"],"FAIL")
        self.assertEqual(transitive_dependency_impact({"A":["missing"]},["A"])["status"],"HOLD")
    def test_puac_control_and_gate_claims_cannot_self_certify(self):
        missing=validate_puac_control("PUAC.C27",{})
        self.assertEqual(missing["status"],"HOLD")
        spoof={"gate_id":"G01","candidate_commit_sha":"a"*40,"package_sha256":"b"*64,
          "trusted_workflow_sha":"c"*40,"producer_identity":"builder","evaluator_identity":"validator",
          "signature_verification":"VERIFIED","evidence_sha256":"d"*64,"status":"PASS"}
        out=evaluate_gate_evidence([spoof],candidate_commit_sha="a"*40,package_sha256="b"*64,
          trusted_workflow_sha="c"*40,producer_identity="builder")
        self.assertFalse(out["release_eligible"])
        self.assertEqual(out["status"],"HOLD")
    def test_every_puac_control_is_bound_to_payload_commit_digest_and_distinct_evaluator(self):
        commit = "a" * 40
        package = "b" * 64
        producer = "candidate-builder"
        for control_id in LOCAL_PUAC_CONTROLS:
            with self.subTest(control_id=control_id):
                evaluator = "independent-validator:" + control_id
                payload = valid_puac_payload(control_id, package, commit, producer, evaluator)
                good = validate_puac_control(control_id, payload, producer_identity=producer,
                    evaluator_identity=evaluator, candidate_sha256=package, candidate_commit_sha=commit)
                self.assertEqual(good["status"], "PASS_FOR_LOCAL_CONTROL_SCOPE", good)
                tampered = dict(payload)
                tampered["evidence_coverage"] = {"candidate_sha256": "c" * 64}
                if control_id != "PUAC.C26":
                    tampered = dict(payload)
                    tampered["evidence_binding"] = dict(payload["evidence_binding"])
                    tampered["evidence_binding"]["candidate_sha256"] = "c" * 64
                    bad = validate_puac_control(control_id, tampered, producer_identity=producer,
                        evaluator_identity=evaluator, candidate_sha256=package, candidate_commit_sha=commit)
                else:
                    tampered = dict(payload)
                    tampered["evidence_coverage"] = {"candidate_sha256": "c" * 64}
                    bad = validate_puac_control(control_id, tampered, producer_identity=producer,
                        evaluator_identity=evaluator, candidate_sha256=package, candidate_commit_sha=commit)
                self.assertEqual(bad["status"], "FAIL")
    def test_puac_binding_absent_or_wrong_commit_is_not_pass(self):
        payload = valid_puac_payload("PUAC.C25", "b" * 64, "a" * 40, "producer", "validator")
        missing = dict(payload)
        missing.pop("evidence_binding")
        self.assertEqual(validate_puac_control("PUAC.C25", missing, candidate_sha256="b" * 64)["status"], "HOLD")
        mismatch = dict(payload)
        mismatch["evidence_binding"] = dict(payload["evidence_binding"])
        mismatch["evidence_binding"]["candidate_commit_sha"] = "d" * 40
        result = validate_puac_control("PUAC.C25", mismatch, producer_identity="producer",
            evaluator_identity="validator", candidate_sha256="b" * 64, candidate_commit_sha="a" * 40)
        self.assertEqual(result["status"], "FAIL")
    def test_complete_gate_bundle_only_passes_binding_layer_not_release(self):
        commit = "a" * 40
        package = "b" * 64
        trust_root = "c" * 40
        producer = "candidate-builder"
        records = []
        for gate in CANONICAL_GATES:
            records.append({"gate_id": gate, "candidate_commit_sha": commit,
                "package_sha256": package, "trusted_workflow_sha": trust_root,
                "producer_identity": producer, "evaluator_identity": "validator:" + gate,
                "evidence_sha256": "d" * 64, "status": "PASS"})
        for gate in LOCAL_PUAC_CONTROLS:
            evaluator = "validator:" + gate
            records.append({"gate_id": gate, "candidate_commit_sha": commit,
                "package_sha256": package, "trusted_workflow_sha": trust_root,
                "producer_identity": producer, "evaluator_identity": evaluator,
                "evidence_sha256": "e" * 64, "status": "PASS",
                "evidence_payload": valid_puac_payload(gate, package, commit, producer, evaluator)})
        report = evaluate_gate_evidence(records, candidate_commit_sha=commit, package_sha256=package,
            trusted_workflow_sha=trust_root, producer_identity=producer,
            trusted_signature_verifier=lambda record: {"status": "PASS", "test_fixture": True},
            applicability_verifier=lambda rows, sha: {"status": "PASS", "applicable_gate_ids": list(CANONICAL_GATES)})
        self.assertEqual(report["status"], "EVIDENCE_BINDINGS_PASS_ONLY", report)
        self.assertFalse(report["release_eligible"])
        self.assertEqual(report["certification"], "NOT_GRANTED_BY_CRFU")
    def test_unknown_and_declared_conflict_claim_states_do_not_look_clean(self):
        base={"claim_id":"claim-1","subject_id":"system","property_id":"ram","scope_id":"build",
          "context_id":"linux-runner","version":"1",
          "validity_interval":{"not_before_utc":"2000-01-01T00:00:00Z","expires_at_utc":"2099-01-01T00:00:00Z"},
          "unit_of_measure":{"unit_id":"byte","dimension":"information","version":"1"},
          "value":100,"evidence_state":"SUPPORTED"}
        unknown=dict(base);unknown["evidence_state"]="UNKNOWN"
        self.assertEqual(classify_claim_conflicts([unknown])["status"],"HOLD")
        declared=dict(base);declared["evidence_state"]="CONFLICT"
        self.assertEqual(classify_claim_conflicts([declared])["status"],"CONFLICT")
        self.assertEqual(classify_claim_conflicts([])["status"],"HOLD")
    def test_claim_conversion_cannot_cross_dimensions_or_drop_original(self):
        base={"claim_id":"claim-conv","subject_id":"x","property_id":"mass","scope_id":"calc",
          "context_id":"unit-test","version":"1",
          "validity_interval":{"not_before_utc":"2000-01-01T00:00:00Z","expires_at_utc":"2099-01-01T00:00:00Z"},
          "unit_of_measure":{"unit_id":"kg","dimension":"mass","version":"1"},
          "value":1,"original_value":1,"evidence_state":"SUPPORTED"}
        conv={"rule_id":"bad-conv","source_unit":{"unit_id":"kg","dimension":"mass","version":"1"},
          "target_unit":{"unit_id":"J","dimension":"energy","version":"1"},"evidence_reference":"evidence://test",
          "original_value":1,"converted_value":42}
        invalid=dict(base);invalid["conversion"]=conv
        self.assertEqual(validate_claim_v2(invalid)["status"],"DENY")
        conv["target_unit"]={"unit_id":"g","dimension":"mass","version":"1"}
        no_preserve=dict(base);no_preserve["conversion"]=dict(conv,original_value=2)
        self.assertEqual(validate_claim_v2(no_preserve)["status"],"DENY")
    def test_coverage_requires_exact_target_and_canonical_cardinality(self):
        requirements=[{"requirement_id":"R1"}]
        self.assertEqual(coverage_report(requirements,["R1"],[])["status"],"HOLD")
        self.assertEqual(coverage_report(requirements,["R1"],[],target_sha256="a"*64,
            required_test_classes=27)["status"],"HOLD")
        report=coverage_report(requirements,["R1"],[
          {"record_type":"TEST_CLASS","test_class_id":"T99","status":"PASS","target_sha256":"a"*64}
        ],target_sha256="a"*64)
        self.assertEqual(report["status"],"FAIL")
        stale=coverage_report(requirements,["R1"],[
          {"requirement_id":"R1","status":"PASS","target_sha256":"b"*64}
        ],target_sha256="a"*64)
        self.assertEqual(stale["status"],"HOLD")
    def test_incident_closure_does_not_imply_reactivation(self):
        evidence={"diagnosis_verified":True,"correction_authorized":True,"correction_executed":True,
          "restoration_verified":True,"nonregression_verified":True,"traceability_complete":True,
          "g23_g24_required":True,"g23_g24_pass":True}
        result=evaluate_incident_closure(evidence)
        self.assertTrue(result["incident_closed"])
        self.assertFalse(result["activation_authorized"])
        self.assertFalse(result["reactivation_authorization_evidence_present"])
    def test_unregistered_gate_identifier_is_denied(self):
        rogue={"gate_id":"G25","candidate_commit_sha":"a"*40,"package_sha256":"b"*64,
          "trusted_workflow_sha":"c"*40,"producer_identity":"producer","evaluator_identity":"validator",
          "evidence_sha256":"d"*64,"status":"PASS"}
        out=evaluate_gate_evidence([rogue],candidate_commit_sha="a"*40,package_sha256="b"*64,
          trusted_workflow_sha="c"*40,producer_identity="producer")
        self.assertEqual(out["status"],"FAIL")
        self.assertIn("UNREGISTERED_GATE_IDENTIFIER",out["reason"])
        self.assertFalse(out["release_eligible"])
    def test_puac_control_requires_exact_candidate_binding_even_when_called_directly(self):
        payload=valid_puac_payload("PUAC.C25","b"*64,"a"*40,"producer","validator")
        result=validate_puac_control("PUAC.C25",payload,producer_identity="producer",evaluator_identity="validator")
        self.assertEqual(result["status"],"HOLD")
        self.assertIn("EXACT_CANDIDATE_DIGEST_REQUIRED",result["reasons"])
    def test_ed25519_attestation_binds_exact_payload_and_public_key(self):
        _, private_pem, public_pem = generate_ed25519_pems()
        payload = {"schema": "TEST/1", "candidate_commit_sha": "a" * 40,
                   "candidate_package_sha256": "b" * 64, "status": "PASS"}
        record = gate_trust_root.sign_record(payload, private_pem, "g23-validator")
        verified, errors = gate_trust_root.verify_signed_record(record, public_pem, "g23-validator", ("producer",))
        self.assertEqual(errors, [])
        self.assertEqual(verified, payload)
        self.assertEqual(record["algorithm"], "Ed25519")
        self.assertEqual(record["payload_sha256"], hashlib.sha256(gate_trust_root.canonical_bytes(payload)).hexdigest())
    def test_ed25519_attestation_rejects_tampering_wrong_identity_and_wrong_key(self):
        _, private_pem, public_pem = generate_ed25519_pems()
        _, _, other_public_pem = generate_ed25519_pems()
        payload = {"schema": "TEST/1", "candidate_commit_sha": "a" * 40}
        record = gate_trust_root.sign_record(payload, private_pem, "g23-validator")
        altered = dict(record)
        altered["payload"] = dict(payload, candidate_commit_sha="c" * 40)
        verified, errors = gate_trust_root.verify_signed_record(altered, public_pem, "g23-validator")
        self.assertIsNone(verified)
        self.assertIn("SIGNED_ATTESTATION_PAYLOAD_HASH_MISMATCH", errors)
        self.assertIn("ED25519_SIGNATURE_INVALID", errors)
        verified, errors = gate_trust_root.verify_signed_record(record, public_pem, "g24-certifier")
        self.assertIsNone(verified)
        self.assertIn("SIGNED_ATTESTATION_SIGNER_IDENTITY_MISMATCH", errors)
        verified, errors = gate_trust_root.verify_signed_record(record, other_public_pem, "g23-validator")
        self.assertIsNone(verified)
        self.assertIn("SIGNED_ATTESTATION_PUBLIC_KEY_FINGERPRINT_MISMATCH", errors)
        self.assertIn("ED25519_SIGNATURE_INVALID", errors)
    def test_g23_g24_private_keys_must_match_configured_public_keys_and_be_distinct(self):
        _, g23_private, g23_public = generate_ed25519_pems()
        _, g24_private, g24_public = generate_ed25519_pems()
        self.assertTrue(gate_trust_root.public_keys_match(g23_private, g23_public))
        self.assertTrue(gate_trust_root.public_keys_match(g24_private, g24_public))
        self.assertFalse(gate_trust_root.public_keys_match(g23_private, g24_public))
        self.assertNotEqual(gate_trust_root.public_key_sha256(g23_public), gate_trust_root.public_key_sha256(g24_public))
        record = gate_trust_root.sign_record({"candidate_package_sha256": "b" * 64}, g23_private, "g23")
        verified, errors = gate_trust_root.verify_signed_record(record, g24_public, "g23")
        self.assertIsNone(verified)
        self.assertTrue(errors)

    def test_g23_g24_attested_scope_certificate_binds_exact_candidate_and_gates(self):
        commit = "a" * 40
        trusted_workflow_sha = "c" * 40
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate_dir = root / "candidate"
            candidate_dir.mkdir()
            package = candidate_dir / "CUSTOSZV9.pyz"
            package.write_bytes(b"test-only-candidate-bytes")
            package_sha = hashlib.sha256(package.read_bytes()).hexdigest()
            g22_path = root / "G22.json"
            g22 = {
                "schema": gate_trust_root.G22_SCHEMA,
                "status": "PASS_FOR_DECLARED_SCOPE",
                "tested_scope_result": "PASS",
                "failures": [],
                "candidate_commit_sha": commit,
                "candidate_package_sha256": package_sha,
                "trusted_workflow_sha": trusted_workflow_sha,
                "local_puac_controls_status": "EVALUATED_FOR_DECLARED_SCOPE_ONLY"
            }
            gate_trust_root.write(g22_path, g22)
            g23_path = root / "G23_UNSIGNED.json"
            g23 = {
                "schema": gate_trust_root.G23_UNSIGNED_SCHEMA,
                "status": "PASS_FOR_DECLARED_SCOPE",
                "tested_scope_result": "PASS",
                "validation_completed": True,
                "candidate_commit_sha": commit,
                "candidate_package_sha256": package_sha,
                "candidate_package_size_bytes": package.stat().st_size,
                "g22_record_sha256": gate_trust_root.sha(g22_path),
                "trusted_workflow_sha": trusted_workflow_sha,
                "producer_identity": "CUSTOSZV9_BUILD_WORKFLOW",
                "validator_identity": "trusted-g23",
                "scope": gate_trust_root.SCOPE,
                "independent_execution_results": [
                    {"name": name, "returncode": 0, "status": "PASS",
                     "stdout_sha256": "d" * 64, "stderr_sha256": "e" * 64}
                    for name in sorted(gate_trust_root.EXPECTED_G23_COMMANDS)
                ],
                "failures": [],
                "scoped_decision_admissible": True,
                "canonical_G23_status": "HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN"
            }
            gate_trust_root.write(g23_path, g23)
            g23_verified = root / "G23_ATTESTATION_VERIFICATION.json"
            g23_verified.write_text('{"verified":true}\n', encoding="utf-8")
            out = root / "CUSTOSZV9_CERTIFICATE.json"
            args = SimpleNamespace(
                candidate_dir=str(candidate_dir), candidate_sha=commit,
                trusted_workflow_sha=trusted_workflow_sha, g22=str(g22_path),
                g23=str(g23_path), g23_attestation_verification=str(g23_verified),
                out=str(out)
            )
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(gate_trust_root.g24(args), 0)
            cert = gate_trust_root.read_json(out)
            self.assertTrue(cert["package_scope_certified"])
            self.assertEqual(cert["decision"], "CERTIFIED_FOR_DECLARED_STANDALONE_SOFTWARE_SCOPE")
            self.assertEqual(cert["candidate_package_sha256"], package_sha)
            self.assertFalse(cert["full_release_eligible"])
            self.assertEqual(cert["canonical_promotion"], "NOT_AUTHORIZED")
            self.assertEqual(cert["canonical_G01_G24_status"], "HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN")

            # Exact candidate-digest or G22-link tampering is fail-closed.
            g23["candidate_package_sha256"] = "f" * 64
            gate_trust_root.write(g23_path, g23)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(gate_trust_root.g24(args), 0)
            held = gate_trust_root.read_json(out)
            self.assertFalse(held["package_scope_certified"])
            self.assertEqual(held["decision"], "HOLD")
            self.assertTrue(held["failures"])

    def test_checkpoint_does_not_prove_restoration(self):
        payload=b"checkpoint";dep=sha256_bytes(b"deps")
        record=checkpoint_record(payload,checkpoint_id="cp",state_identity="s",dependency_fingerprint=dep)
        self.assertFalse(record["restoration_proven"])
        out=verify_restoration(record,payload,expected_state_identity="s",
            expected_dependency_fingerprint=dep,invariants_pass=True,journal_valid=True)
        self.assertTrue(out["restoration_proven"])
        bad=verify_restoration(record,b"changed",expected_state_identity="s",
            expected_dependency_fingerprint=dep,invariants_pass=True,journal_valid=True)
        self.assertFalse(bad["restoration_proven"])


    def test_full_bounded_offline_crfu_selftest(self):
        from custoszv9.crfu.selftest import run_selftest
        result = run_selftest()
        self.assertEqual(result["status"], "PASS", result.get("failed_checks"))
        self.assertEqual(result["schema"], "CUSTOSZV9_CRFU_SELFTEST/2.0")
        self.assertGreaterEqual(result["check_count"], 10)
        self.assertTrue(result["checks"]["bounded_256_action_stress"])
        self.assertTrue(result["checks"]["offline_checkpoint_restore_postvalidated"])
        self.assertTrue(result["checks"]["bounded_queue_32_missions_and_hash_chain"])
        self.assertTrue(result["checks"]["journal_tamper_detected"])
        self.assertTrue(result["checks"]["missing_formal_proof_fails_closed"])
        self.assertFalse(result["authorization_granted"])
        self.assertFalse(result["external_host_operations"])
        self.assertEqual(result["certification"], "NOT_GRANTED_BY_SELFTEST")


    def test_runtime_resource_decision_matches_formal_predicates_on_bounded_domain(self):
        """Exhaustively check the Agda-aligned guards on a finite input domain.

        This is bounded differential regression evidence, not a universal proof that
        arbitrary Python execution refines the Agda model. The universal bridge remains
        an explicit assurance obligation and must not be certified from finite tests.
        """
        from itertools import product

        checked = 0
        for (
            ram_required,
            ram_reserved,
            ram_available,
            disk_required,
            disk_available,
            cpu_count,
            concurrency,
        ) in product(range(4), repeat=7):
            snapshot = self._measured_snapshot(
                ram=ram_available,
                disk=disk_available,
                cpu=cpu_count,
            )
            result = evaluate_budget(
                ResourceBudget(
                    ram_required,
                    ram_reserved,
                    disk_required,
                    concurrency,
                ),
                snapshot,
            )

            # Direct correspondence to the normalized Agda guard predicates:
            # requiredRam + reservedRam < availableRam;
            # requiredDisk < availableDisk;
            # 1 <= concurrency <= max(1, cpuCount).
            formal_guards = (
                ram_required + ram_reserved < ram_available
                and disk_required < disk_available
                and concurrency >= 1
                and concurrency <= max(1, cpu_count)
            )
            expected = "PASS" if formal_guards else "FAIL"
            self.assertEqual(
                result["status"],
                expected,
                msg=(
                    "runtime/formal-guard status mismatch",
                    ram_required,
                    ram_reserved,
                    ram_available,
                    disk_required,
                    disk_available,
                    cpu_count,
                    concurrency,
                ),
            )
            checked += 1

        self.assertEqual(checked, 4**7)

if __name__=="__main__":
    unittest.main()
