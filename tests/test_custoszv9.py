from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path
from custoszv9.crfu.anti_paralysis import decide_next_action, state_fingerprint, retry_decision
from custoszv9.crfu.evidence import append_event, verify_journal
from custoszv9.crfu.event_queue import PersistentMissionQueue
from custoszv9.crfu.formal import validate_proof_bundle
from custoszv9.crfu.gates import CANONICAL_GATES, LOCAL_PUAC_CONTROLS, evaluate_gate_evidence
from custoszv9.crfu.model import sha256_bytes
from custoszv9.crfu.planner import ActionSpec, build_plan
from custoszv9.crfu.recovery import checkpoint_record, verify_restoration
from custoszv9.crfu.resources import ResourceBudget, ResourceSnapshot, evaluate_budget
from custoszv9.crfu.puac2 import (
    classify_claim_conflicts, coverage_report, evaluate_incident_closure,
    transitive_dependency_impact, validate_authority_binding, validate_claim_v2,
    validate_event_records, validate_puac_control, validate_recovery_plan
)

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
          trust_verifier=lambda b:{"status":"PASS","binding_id":b["binding_id"],"least_privilege_verified":True})
        self.assertEqual(passed["status"],"PASS")
        self.assertEqual(validate_authority_binding(binding,action="delete",object_id="repo",scope_id="feature-branch",
          trust_verifier=lambda b:{"status":"PASS","binding_id":b["binding_id"],"least_privilege_verified":True})["status"],"DENY")
    def test_recovery_plan_does_not_claim_restoration_or_activation(self):
        plan={"incident_id":"i1","authorized_actor":"actor","checkpoint_id":"cp",
          "checkpoint_hash":sha256_bytes(b"snapshot"),"target_environment":"test-host","dependency_hashes":[sha256_bytes(b"dep")],
          "restoration_oracles":["state-hash"],"nonregression_plan":"run checks","rollback_scope":"local",
          "irreversible_side_effects":[],"authority_ref":"binding"}
        self.assertEqual(validate_recovery_plan(plan)["status"],"PASS")
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

if __name__=="__main__":
    unittest.main()
