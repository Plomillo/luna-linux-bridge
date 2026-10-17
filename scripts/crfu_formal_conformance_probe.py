#!/usr/bin/env python3
"""Trusted finite conformance probes for the unchanged CUSTOSZV9 runtime.

This is evidence of bounded behavioral correspondence only, not a proof of
universal Python-to-Agda refinement. It imports only runtime source files whose
bytes G22 independently compared against the protected candidate baseline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import tempfile
from typing import Callable


IMPLEMENTATION_PATHS = [
    "custoszv9/__init__.py",
    "custoszv9/crfu/__init__.py",
    "custoszv9/crfu/model.py",
    "custoszv9/crfu/anti_paralysis.py",
    "custoszv9/crfu/coordinator.py",
    "custoszv9/crfu/event_queue.py",
    "custoszv9/crfu/planner.py",
    "custoszv9/crfu/resources.py",
    "custoszv9/crfu/recovery.py",
    "custoszv9/crfu/equivalence.py",
    "custoszv9/crfu/formal.py",
    "custoszv9/crfu/gates.py",
    "custoszv9/crfu/puac2.py",
    "custoszv9/crfu/contracts.py",
    "custoszv9/crfu/migration.py",
]


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: pathlib.Path) -> str:
    return sha_bytes(path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--g22", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = pathlib.Path(args.source_root).resolve()
    g22_path = pathlib.Path(args.g22)
    g22 = json.loads(g22_path.read_text(encoding="utf-8"))
    assert g22.get("schema") == "CRFU_FORMAL_G22/1.0"
    assert g22.get("status") == "PASS"
    assert g22.get("candidate_formal_source_commit") == args.candidate_sha
    assert g22.get("baseline_candidate_commit") == args.baseline_sha

    entries = g22.get("implementation_files")
    assert isinstance(entries, list), "G22_IMPLEMENTATION_MANIFEST_MISSING"
    assert sorted(row.get("path") for row in entries) == sorted(IMPLEMENTATION_PATHS), (
        "G22_IMPLEMENTATION_FILE_SET_MISMATCH"
    )
    for item in entries:
        path = root / item["path"]
        assert path.is_file(), "IMPLEMENTATION_FILE_MISSING:" + item["path"]
        assert path.stat().st_size == item["bytes"], "IMPLEMENTATION_SIZE_MISMATCH:" + item["path"]
        assert sha_file(path) == item["sha256"], "IMPLEMENTATION_HASH_MISMATCH:" + item["path"]
        assert item["sha256"] == item["baseline_sha256"], (
            "IMPLEMENTATION_NOT_IDENTICAL_TO_BASELINE:" + item["path"]
        )

    # Imports occur only after the runtime file set is bound to G22 and its baseline.
    sys.path.insert(0, str(root))
    from custoszv9.crfu.coordinator import run_bounded_mission
    from custoszv9.crfu.event_queue import PersistentMissionQueue, QueueConflict, InvalidTransition
    from custoszv9.crfu.equivalence import validate_equivalence
    from custoszv9.crfu.formal import validate_proof_bundle
    from custoszv9.crfu.gates import evaluate_gate_evidence
    from custoszv9.crfu.model import TaskContract
    from custoszv9.crfu.planner import ActionSpec, build_plan
    from custoszv9.crfu.recovery import checkpoint_record, verify_restoration
    from custoszv9.crfu.resources import ResourceBudget, ResourceSnapshot, evaluate_budget
    from custoszv9.crfu.contracts import RuntimeContract, run_composed_contracts
    from custoszv9.crfu.migration import MigrationWitness, validate_migration_witness

    observations: list[dict[str, str]] = []

    def task_value(task_id: str = "task-1") -> dict:
        return {
            "task_id": task_id,
            "mission_id": "mission-1",
            "project_id": "project-1",
            "source_identity": "source-v1",
            "target_identity": "target-v1",
            "source_state_hash": "d" * 64,
            "dependency_set": [],
            "authorized_scope": "bounded-conformance",
            "required_capabilities": [],
            "inputs": [],
            "preconditions": [],
            "permitted_effects": [],
            "resource_budget": {
                "ram_required_bytes": 100,
                "ram_reserved_bytes": 50,
                "disk_required_bytes": 100,
                "max_concurrency": 1,
            },
            "execution_deadline": "2099-01-01T00:00:00Z",
            "maximum_planning_budget": 4,
            "maximum_retry_budget": 0,
            "acceptance_criteria": [],
            "expected_outputs": [],
            "validation_strategy": "independent-check",
            "evidence_requirements": [],
            "checkpoint_reference": "checkpoint-1",
            "rollback_strategy": "restore-and-verify",
            "completion_condition": "all-actions-pass",
            "escalation_condition": "hold-on-unknown",
            "authorization_evidence_reference": "auth-evidence-1",
        }

    def coordinator_snapshot():
        return ResourceSnapshot(
            ram_available_bytes=10000,
            disk_available_bytes=20000,
            cpu_count=2,
            measured_at_utc="2026-01-01T00:00:00Z",
            source="trusted-conformance-fixture",
            confidence="MEASURED",
        )

    def check(name: str, fn: Callable[[], None]) -> None:
        fn()
        observations.append({"name": name, "status": "PASS"})

    def action(action_id, dependencies=(), caps=(), effects=()):
        return ActionSpec(
            action_id=action_id,
            dependencies=tuple(dependencies),
            required_capabilities=tuple(caps),
            permitted_effects=tuple(effects),
            idempotency="READ_ONLY",
        )

    check(
        "planner.valid_topological_order_and_no_execution_authority",
        lambda: _assert_plan(
            build_plan(
                [action("b", dependencies=("a",)), action("a")],
                max_alternatives=8,
                available_capabilities=set(),
                admissible_effects=set(),
            ),
            "PLAN_VALIDATED",
            ordered=["a", "b"],
            execution_authorized=False,
        ),
    )
    check(
        "planner.missing_dependency_holds",
        lambda: _assert_plan(
            build_plan([action("x", dependencies=("missing",))], max_alternatives=8,
                       available_capabilities=set(), admissible_effects=set()),
            "HOLD",
            reason="DEPENDENCY_UNRESOLVED",
        ),
    )
    check(
        "planner.cycle_denied",
        lambda: _assert_plan(
            build_plan([action("a", ("b",)), action("b", ("a",))], max_alternatives=8,
                       available_capabilities=set(), admissible_effects=set()),
            "DENIED",
            reason="DEPENDENCY_CYCLE",
        ),
    )
    check(
        "planner.duplicate_ids_denied",
        lambda: _assert_plan(
            build_plan([action("a"), action("a")], max_alternatives=8,
                       available_capabilities=set(), admissible_effects=set()),
            "DENIED",
            reason="DUPLICATE_ACTION_ID:a",
        ),
    )
    check(
        "planner.missing_capability_denied",
        lambda: _assert_plan(
            build_plan([action("read", caps=("filesystem.read",))], max_alternatives=8,
                       available_capabilities=set(), admissible_effects=set()),
            "DENIED",
            reason="ACTION_NOT_ADMISSIBLE",
        ),
    )
    check(
        "planner.forbidden_effect_denied",
        lambda: _assert_plan(
            build_plan([action("write", effects=("network.write",))], max_alternatives=8,
                       available_capabilities=set(), admissible_effects=set()),
            "DENIED",
            reason="ACTION_NOT_ADMISSIBLE",
        ),
    )
    check(
        "planner.alternative_budget_holds",
        lambda: _assert_plan(
            build_plan([action("a"), action("b")], max_alternatives=1,
                       available_capabilities=set(), admissible_effects=set()),
            "HOLD",
            reason="ALTERNATIVE_BUDGET_EXCEEDED",
        ),
    )

    good_snapshot = ResourceSnapshot(
        ram_available_bytes=1000,
        disk_available_bytes=2000,
        cpu_count=4,
        measured_at_utc="2026-01-01T00:00:00Z",
        source="formal-conformance-fixture",
        confidence="MEASURED",
    )
    good_budget = ResourceBudget(
        ram_required_bytes=200, ram_reserved_bytes=100,
        disk_required_bytes=400, max_concurrency=2,
    )
    check(
        "resources.measured_in_budget_passes",
        lambda: _assert_status(evaluate_budget(good_budget, good_snapshot), "PASS"),
    )
    unknown_snapshot = ResourceSnapshot(
        ram_available_bytes=None, disk_available_bytes=None, cpu_count=None,
        measured_at_utc="2026-01-01T00:00:00Z", source="UNKNOWN", confidence="UNKNOWN",
    )
    check(
        "resources.unknown_measurement_holds",
        lambda: _assert_status(
            evaluate_budget(good_budget, unknown_snapshot), "HOLD",
            expected_reason="RAM_AVAILABLE_BYTES_UNKNOWN",
        ),
    )
    check(
        "resources.ram_over_budget_fails",
        lambda: _assert_status(
            evaluate_budget(
                ResourceBudget(900, 200, 100, 2),
                ResourceSnapshot(1000, 2000, 4, "2026-01-01T00:00:00Z", "test", "MEASURED"),
            ),
            "FAIL",
            expected_reason="RAM_BUDGET_EXCEEDED",
        ),
    )
    check(
        "resources.disk_over_budget_fails",
        lambda: _assert_status(
            evaluate_budget(ResourceBudget(100, 0, 2001, 2), good_snapshot),
            "FAIL",
            expected_reason="DISK_BUDGET_EXCEEDED",
        ),
    )
    check(
        "resources.invalid_concurrency_fails",
        lambda: _assert_status(
            evaluate_budget(ResourceBudget(100, 0, 100, 5), good_snapshot),
            "FAIL",
            expected_reason="CONCURRENCY_BUDGET_INVALID",
        ),
    )

    payload = b"checkpoint-payload-v1"
    dep_fp = sha_bytes(b"dependency-fingerprint")
    checkpoint = checkpoint_record(
        payload, checkpoint_id="cp-1", state_identity="state-v1",
        dependency_fingerprint=dep_fp,
    )

    def restore(**overrides):
        values = dict(
            record=checkpoint,
            restored_payload=payload,
            expected_state_identity="state-v1",
            expected_dependency_fingerprint=dep_fp,
            invariants_pass=True,
            journal_valid=True,
        )
        values.update(overrides)
        return verify_restoration(**values)

    check("recovery.exact_bytes_state_dependencies_and_journal_pass",
          lambda: _assert_restore(restore(), "PASS"))
    check("recovery.changed_bytes_blocked",
          lambda: _assert_restore(restore(restored_payload=b"tampered"), "BLOCKED",
                                  reason="RESTORED_BYTES_MISMATCH"))
    check("recovery.changed_state_identity_blocked",
          lambda: _assert_restore(restore(expected_state_identity="wrong"), "BLOCKED",
                                  reason="RESTORED_STATE_IDENTITY_MISMATCH"))
    check("recovery.changed_dependency_fingerprint_blocked",
          lambda: _assert_restore(restore(expected_dependency_fingerprint=sha_bytes(b"wrong")), "BLOCKED",
                                  reason="RESTORED_DEPENDENCY_MISMATCH"))
    check("recovery.unproven_invariants_blocked",
          lambda: _assert_restore(restore(invariants_pass=False), "BLOCKED",
                                  reason="RESTORED_INVARIANTS_NOT_PROVEN"))
    check("recovery.invalid_journal_blocked",
          lambda: _assert_restore(restore(journal_valid=False), "BLOCKED",
                                  reason="EVIDENCE_JOURNAL_INVALID"))

    valid_equivalence = {
        "source_sha256": "a" * 64,
        "target_sha256": "b" * 64,
        "equivalence_specification_id": "EQ-SPEC-1",
        "specification_sha256": "c" * 64,
        "proof_status": "VERIFIED",
        "proof_verified_by": "independent-evaluator",
        "producer_identity": "producer",
        "transportable_properties": ["logical-claim"],
    }
    check(
        "equivalence.independently_verified_scoped_claim_admissible",
        lambda: _assert_equivalence(validate_equivalence(valid_equivalence),
                                    "ADMISSIBLE_FOR_DECLARED_SCOPE"),
    )
    check(
        "equivalence.missing_proof_unproven",
        lambda: _assert_equivalence(
            validate_equivalence({**valid_equivalence, "proof_status": "UNKNOWN"}),
            "UNPROVEN",
        ),
    )
    check(
        "equivalence.producer_cannot_self_verify",
        lambda: _assert_equivalence(
            validate_equivalence({**valid_equivalence, "proof_verified_by": "producer"}),
            "UNPROVEN",
        ),
    )
    check(
        "equivalence.certification_cannot_be_transported",
        lambda: _assert_equivalence(
            validate_equivalence({
                **valid_equivalence,
                "transportable_properties": ["logical-claim", "certification"],
            }),
            "UNPROVEN",
            reason_prefix="FORBIDDEN_PROPERTY_TRANSPORT:",
        ),
    )

    valid_bundle = {
        "target_sha256": "d" * 64,
        "scope": "bounded-conformance",
        "specification_sha256": "e" * 64,
        "toolchain": {"name": "Agda", "version": "2.8.0.2"},
        "assumptions": [],
        "limitations": ["bounded probes do not prove universal refinement"],
        "status": "PASS_WITH_LIMITATIONS",
        "evidence_verified": True,
        "transportable_properties": ["listed-probe-observations"],
    }
    check(
        "formal.bundle_with_explicit_limits_accepted_only_for_declared_scope",
        lambda: _assert_proof_bundle(
            validate_proof_bundle(valid_bundle, "d" * 64, "bounded-conformance"),
            "PASS_FOR_DECLARED_SCOPE",
        ),
    )
    check(
        "formal.absent_proof_bundle_holds",
        lambda: _assert_proof_bundle(
            validate_proof_bundle(None, "d" * 64, "bounded-conformance"),
            "HOLD",
        ),
    )
    check(
        "gates.missing_global_evidence_remains_hold",
        lambda: _assert_gate_hold(evaluate_gate_evidence(
            [], candidate_commit_sha="a" * 40, package_sha256="b" * 64,
            trusted_workflow_sha="c" * 40, producer_identity="producer",
        )),
    )

    def valid_task_contract():
        task, issues = TaskContract.validate(task_value())
        assert task is not None and issues == [], {"task": task is not None, "issues": issues}

    def invalid_task_contract_hash():
        raw = task_value()
        raw["source_state_hash"] = "not-a-digest"
        task, issues = TaskContract.validate(raw)
        assert task is None and "SOURCE_STATE_HASH_INVALID" in issues, issues

    check("task_contract.valid_typed_contract_passes", valid_task_contract)
    check("task_contract.invalid_source_state_hash_is_rejected", invalid_task_contract_hash)

    def run_coordinator(authorization_verifier, action_runner):
        return run_bounded_mission(
            task_value(),
            [action("action-1")],
            coordinator_snapshot(),
            available_capabilities=set(),
            admissible_effects=set(),
            authorization_verifier=authorization_verifier,
            action_runner=action_runner,
            maximum_steps=1,
            planning_budget=2,
        )

    check(
        "coordinator.missing_authorization_verifier_holds",
        lambda: _assert_stage(
            run_coordinator(None, lambda ctx: {"status": "PASS"}),
            "HOLD", "AUTHORIZATION",
        ),
    )
    check(
        "coordinator.authorization_bound_to_wrong_task_is_denied",
        lambda: _assert_stage(
            run_coordinator(
                lambda task: {"status": "PASS", "task_id": "different-task"},
                lambda ctx: {"status": "PASS"},
            ),
            "DENIED", "AUTHORIZATION",
        ),
    )
    check(
        "coordinator.missing_action_adapter_holds",
        lambda: _assert_stage(
            run_coordinator(
                lambda task: {"status": "PASS", "task_id": task["task_id"]}, None
            ),
            "HOLD", "EXECUTION",
        ),
    )

    def successful_bounded_mission():
        result = run_coordinator(
            lambda task: {"status": "PASS", "task_id": task["task_id"]},
            lambda ctx: {"status": "PASS", "result_state_hash": "f" * 64},
        )
        assert result.get("status") == "COMPLETED", result
        assert result.get("completion_claim") is True, result
        assert result.get("certification") == "NOT_GRANTED", result
        assert result.get("canonical_promotion") == "NOT_AUTHORIZED", result

    check(
        "coordinator.valid_scope_bound_mission_completes_without_certification",
        successful_bounded_mission,
    )

    def queue_duplicate_and_conflict():
        with tempfile.TemporaryDirectory() as directory:
            queue = PersistentMissionQueue(pathlib.Path(directory) / "missions.sqlite")
            first = queue.submit(task_value())
            again = queue.submit(task_value())
            assert first["idempotent_duplicate"] is False, first
            assert again["idempotent_duplicate"] is True and again["state"] == "RECEIVED", again
            changed = task_value()
            changed["target_identity"] = "different-target"
            try:
                queue.submit(changed)
            except QueueConflict:
                return
            raise AssertionError("REUSED_MISSION_ID_WITH_CHANGED_TASK_WAS_ACCEPTED")

    check(
        "queue.identical_resubmission_is_idempotent_and_changed_task_conflicts",
        queue_duplicate_and_conflict,
    )

    def queue_valid_transitions_and_event_chain():
        with tempfile.TemporaryDirectory() as directory:
            queue = PersistentMissionQueue(pathlib.Path(directory) / "missions.sqlite")
            queue.submit(task_value())
            queue.transition("task-1", "RECEIVED", "PREFLIGHT", event_type="PREFLIGHT_STARTED")
            queue.transition("task-1", "PREFLIGHT", "READY", event_type="PREFLIGHT_PASSED")
            running = queue.claim_next_ready()
            assert running is not None and running["state"] == "RUNNING", running
            chain = queue.verify_event_chain()
            assert chain.get("status") == "PASS" and chain.get("event_count") == 4, chain

    check(
        "queue.allowed_transitions_claim_one_ready_task_and_verify_hash_chain",
        queue_valid_transitions_and_event_chain,
    )

    def queue_forbidden_transition():
        with tempfile.TemporaryDirectory() as directory:
            queue = PersistentMissionQueue(pathlib.Path(directory) / "missions.sqlite")
            queue.submit(task_value())
            try:
                queue.transition("task-1", "RECEIVED", "RUNNING", event_type="FORBIDDEN_SKIP")
            except InvalidTransition:
                return
            raise AssertionError("FORBIDDEN_STATE_TRANSITION_WAS_ACCEPTED")

    check("queue.forbidden_transition_is_denied", queue_forbidden_transition)

    def queue_wait_condition_and_deadline():
        with tempfile.TemporaryDirectory() as directory:
            queue = PersistentMissionQueue(pathlib.Path(directory) / "missions.sqlite")
            queue.submit(task_value())
            queue.transition("task-1", "RECEIVED", "PREFLIGHT", event_type="PREFLIGHT_STARTED")
            queue.transition(
                "task-1",
                "PREFLIGHT",
                "WAITING_FOR_EVENT",
                event_type="WAIT_DECLARED",
                fields={
                    "wait_condition": "schema-ready",
                    "wait_deadline_utc": "2099-01-01T00:00:00Z",
                },
            )
            wrong = queue.emit_signal("different-signal")
            assert wrong["resumed"] == [], wrong
            assert queue.get("task-1")["state"] == "WAITING_FOR_EVENT"
            correct = queue.emit_signal("schema-ready")
            assert correct["resumed"] == ["task-1"], correct
            assert queue.get("task-1")["state"] == "READY"
            chain = queue.verify_event_chain()
            assert chain.get("status") == "PASS" and chain.get("event_count") == 4, chain

    check(
        "queue.only_matching_event_resumes_bounded_wait_and_chain_verifies",
        queue_wait_condition_and_deadline,
    )


    # Runtime checks newly tied to the Agda Hoare/migration model sources.
    first_contract = RuntimeContract(
        "increment", lambda x: type(x) is int and x >= 0,
        lambda x: x + 1, lambda before, after: after == before + 1,
    )
    second_contract_calls = []
    second_contract = RuntimeContract(
        "double", lambda x: type(x) is int and x >= 1,
        lambda x: second_contract_calls.append(x) or x * 2,
        lambda before, after: after == before * 2,
    )
    check(
        "contracts.postcondition_bridge_precondition_and_second_postcondition_pass",
        lambda: _assert_composed_contract(
            run_composed_contracts(
                first_contract, second_contract,
                lambda before, middle: middle == before + 1, 1,
            ),
            "PASS_FOR_DECLARED_CONTRACTS",
        ),
    )
    second_contract_calls.clear()
    check(
        "contracts.failed_bridge_holds_and_prevents_second_execution",
        lambda: _assert_composed_contract(
            run_composed_contracts(
                first_contract, second_contract, lambda before, middle: False, 1,
            ),
            "HOLD", reason="POST_PRE_BRIDGE_NOT_ESTABLISHED", calls=second_contract_calls,
        ),
    )
    check(
        "contracts.first_postcondition_failure_fails_closed",
        lambda: _assert_composed_contract(
            run_composed_contracts(
                RuntimeContract("broken", lambda x: True, lambda x: x + 1,
                                lambda before, after: False),
                second_contract, lambda before, middle: True, 1,
            ),
            "FAIL", reason="FIRST_POSTCONDITION_FAILED",
        ),
    )

    migration_source = b"migration-source-v1"
    migration_target = b"migration-target-v2"
    valid_migration = MigrationWitness(
        source_version="v1", target_version="v2",
        source_artifact_sha256=sha_bytes(migration_source),
        target_artifact_sha256=sha_bytes(migration_target),
        invariant_id="declared-state-invariant",
        invariant_proof_sha256=sha_bytes(b"proof-record"),
        proof_status="VERIFIED", producer_identity="migration-producer",
        verifier_identity="independent-verifier",
        rollback_artifact_sha256=sha_bytes(b"rollback-artifact"),
    )
    check(
        "migration.exact_artifacts_and_independent_declared_invariant_pass",
        lambda: _assert_migration(
            validate_migration_witness(
                valid_migration, migration_source, migration_target,
                source_invariant_holds=True, target_invariant_holds=True,
            ),
            "PASS_FOR_DECLARED_INVARIANT",
        ),
    )
    check(
        "migration.target_digest_mismatch_fails",
        lambda: _assert_migration(
            validate_migration_witness(
                valid_migration, migration_source, b"tampered",
                source_invariant_holds=True, target_invariant_holds=True,
            ),
            "FAIL", reason="MIGRATION_TARGET_ARTIFACT_MISMATCH",
        ),
    )
    check(
        "migration.same_producer_verifier_holds",
        lambda: _assert_migration(
            validate_migration_witness(
                MigrationWitness(
                    source_version="v1", target_version="v2",
                    source_artifact_sha256=sha_bytes(migration_source),
                    target_artifact_sha256=sha_bytes(migration_target),
                    invariant_id="declared-state-invariant",
                    invariant_proof_sha256=sha_bytes(b"proof-record"),
                    proof_status="VERIFIED", producer_identity="same",
                    verifier_identity="same",
                    rollback_artifact_sha256=sha_bytes(b"rollback-artifact"),
                ),
                migration_source, migration_target,
                source_invariant_holds=True, target_invariant_holds=True,
            ),
            "HOLD", reason="MIGRATION_REQUIRES_INDEPENDENT_VERIFIER",
        ),
    )
    check(
        "migration.malformed_rollback_digest_holds",
        lambda: _assert_migration(
            validate_migration_witness(
                MigrationWitness(
                    source_version="v1", target_version="v2",
                    source_artifact_sha256=sha_bytes(migration_source),
                    target_artifact_sha256=sha_bytes(migration_target),
                    invariant_id="declared-state-invariant",
                    invariant_proof_sha256=sha_bytes(b"proof-record"),
                    proof_status="VERIFIED", producer_identity="producer",
                    verifier_identity="reviewer", rollback_artifact_sha256="invalid",
                ),
                migration_source, migration_target,
                source_invariant_holds=True, target_invariant_holds=True,
            ),
            "HOLD", reason="MIGRATION_DIGEST_INVALID",
        ),
    )

    mapping = [
        {
            "formal_module": "PlanSoundness.agda",
            "runtime_symbols": ["custoszv9.crfu.planner.build_plan"],
            "coverage": "PARTIAL_BOUNDED_PROBES",
            "boundary": "Planner probes cover dependency/capability/effect guards and confirm execution_authorized=false; resource budget is checked separately; no formal theorem links the full Python graph algorithm to Agda.",
        },
        {
            "formal_module": "ResourceBudgetModel.agda",
            "runtime_symbols": ["custoszv9.crfu.resources.evaluate_budget"],
            "coverage": "BOUNDED_BOUNDARY_PROBES",
            "boundary": "Tests selected measured/unknown/RAM/disk/concurrency cases, not every host or all integer values.",
        },
        {
            "formal_module": "RecoveryInvariant.agda",
            "runtime_symbols": ["custoszv9.crfu.recovery.verify_restoration"],
            "coverage": "BOUNDED_NEGATIVE_AND_POSITIVE_PROBES",
            "boundary": "Tests byte/state/dependency/invariant/journal conditions on selected fixtures; not production rollback.",
        },
        {
            "formal_module": "EquivalenceTransport.agda",
            "runtime_symbols": ["custoszv9.crfu.equivalence.validate_equivalence"],
            "coverage": "BOUNDED_POSITIVE_AND_NEGATIVE_PROBES",
            "boundary": "Tests independent evidence and denial of certification transport; not a universal equivalence theorem.",
        },
        {
            "formal_module": "ContractComposition.agda",
            "runtime_symbols": ["custoszv9.crfu.model.TaskContract.validate", "custoszv9.crfu.coordinator.run_bounded_mission"],
            "coverage": "PARTIAL_BOUNDED_MISSION_PIPELINE_PROBES",
            "boundary": "Task validation, authorization, resource, plan and action-adapter gates are exercised; no theorem establishes complete Python-to-Agda contract-composition refinement.",
        },
        {
            "formal_module": "ContractHoareComposition.agda",
            "runtime_symbols": ["custosz9.crfu.contracts.run_composed_contracts"],
            "coverage": "BOUNDED_RUNTIME_COMPOSITION_WITNESS",
            "boundary": "Runtime requires first precondition, first postcondition, explicit post-to-pre bridge, second precondition and second postcondition. Python callbacks are runtime witnesses, not Agda proof terms.",
        },
        {
            "formal_module": "MigrationSimulation.agda",
            "runtime_symbols": ["custosz9.crfu.migration.validate_migration_witness"],
            "coverage": "BOUNDED_EXACT_ARTIFACT_AND_INVARIANT_WITNESS",
            "boundary": "Source/target bytes and versions, declared invariant, proof digest syntax, independent identities, and rollback digest syntax are checked. This is not a universal migration-semantics theorem.",
        },
        {
            "formal_module": "MigrationCoherence.agda",
            "runtime_symbols": ["custosz9.crfu.migration.validate_migration_witness"],
            "coverage": "BOUNDED_RUNTIME_WITNESS_NOT_UNIVERSAL_REFINEMENT",
            "boundary": "Runtime witness is tied to exact source/target artifacts and one declared invariant; no universal migration-semantics theorem is claimed.",
        },
        {
            "formal_module": "ModelImplementationCorrespondence.agda",
            "runtime_symbols": [
                "custoszv9.crfu.formal.validate_proof_bundle",
                "custoszv9.crfu.gates.evaluate_gate_evidence",
            ],
            "coverage": "EVIDENCE_GATES_TESTED_BUT_REFINEMENT_NOT_PROVEN",
            "boundary": "Evidence-admission behavior is probed; the module does not establish a proof from Python source semantics to Agda semantics.",
        },
        {
            "formal_module": "TaskAndStateModel.agda",
            "runtime_symbols": ["custoszv9.crfu.model.TaskContract.validate", "custoszv9.crfu.event_queue.PersistentMissionQueue"],
            "coverage": "BOUNDED_TASK_AND_STATE_PROBES",
            "boundary": "Typed task validation, allowed queue transitions, idempotent submission, bounded event waits and event hash-chain verification are tested; this is not a universal state-machine refinement theorem.",
        },
    ]

    implementation_manifest = [
        {k: row[k] for k in ("path", "bytes", "sha256", "baseline_sha256")}
        for row in sorted(entries, key=lambda row: row["path"])
    ]
    manifest_sha = sha_bytes(json.dumps(
        implementation_manifest, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"))
    output = {
        "schema": "CRFU_PYTHON_CONFORMANCE_G23/1.0",
        "status": "PASS_BOUNDED_CONFORMANCE",
        "candidate_formal_source_commit": args.candidate_sha,
        "baseline_candidate_commit": args.baseline_sha,
        "g22_record_sha256": sha_file(g22_path),
        "implementation_manifest_sha256": manifest_sha,
        "implementation_files": implementation_manifest,
        "trusted_probe_sha256": sha_file(pathlib.Path(__file__)),
        "checks_passed": len(observations),
        "checks_failed": 0,
        "observations": observations,
        "mapping": mapping,
        "claim_boundary": {
            "positive": "The listed independent runtime probes passed against byte-identical runtime modules from the previously scoped V9 source baseline.",
            "not_claimed": [
                "universal Python-to-Agda refinement",
                "complete semantics-preserving translation",
                "proof of every invariant of Louksna",
                "production rollback or host mTLS correctness",
                "canonical promotion or operational authorization"
            ]
        }
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "checks_passed": output["checks_passed"],
        "implementation_manifest_sha256": manifest_sha,
        "trusted_probe_sha256": output["trusted_probe_sha256"],
        "unmapped_formal_modules": [
            row["formal_module"] for row in mapping
            if row["coverage"].startswith("NOT_")
        ],
    }, indent=2))
    return 0


def _assert_composed_contract(result, expected_status, *, reason=None, calls=None):
    assert result.get("status") == expected_status, result
    assert result.get("execution_authorized") is False, result
    assert result.get("certification_propagation") is False, result
    assert result.get("authority_transfer") is False, result
    if reason is not None:
        assert result.get("reason") == reason, result
    if calls is not None:
        assert calls == [], calls


def _assert_migration(result, expected_status, *, reason=None):
    assert result.get("status") == expected_status, result
    assert result.get("certification_propagation") is False, result
    assert result.get("authority_transfer") is False, result
    if reason is not None:
        assert result.get("reason") == reason, result
    if expected_status == "PASS_FOR_DECLARED_INVARIANT":
        assert result.get("universal_migration_refinement_proven") is False, result


def _assert_plan(result, expected_status, *, ordered=None, reason=None, execution_authorized=None):
    assert result.get("status") == expected_status, result
    if ordered is not None:
        assert result.get("ordered_actions") == ordered, result
    if reason is not None:
        assert result.get("reason") == reason, result
    if execution_authorized is not None:
        assert result.get("execution_authorized") is execution_authorized, result


def _assert_status(result, expected_status, *, expected_reason=None):
    assert result.get("status") == expected_status, result
    if expected_reason is not None:
        assert expected_reason in result.get("reasons", []), result


def _assert_restore(result, expected_status, *, reason=None):
    assert result.get("status") == expected_status, result
    if reason is not None:
        assert reason in result.get("failures", []), result
    if expected_status == "PASS":
        assert result.get("restoration_proven") is True
    else:
        assert result.get("restoration_proven") is False
        assert result.get("certification_propagation") is False


def _assert_equivalence(result, expected_status, *, reason_prefix=None):
    assert result.get("status") == expected_status, result
    if expected_status == "ADMISSIBLE_FOR_DECLARED_SCOPE":
        assert result.get("authority_transfer") is False
        assert result.get("certification_transfer") is False
    if reason_prefix is not None:
        assert any(x.startswith(reason_prefix) for x in result.get("issues", [])), result


def _assert_proof_bundle(result, expected_status):
    assert result.get("status") == expected_status, result
    if expected_status == "HOLD":
        assert result.get("proof_transport") == "DENIED"


def _assert_stage(result, expected_status, expected_stage):
    assert result.get("status") == expected_status, result
    assert result.get("stage") == expected_stage, result


def _assert_gate_hold(result):
    assert result.get("status") == "HOLD", result
    assert result.get("release_eligible") is False, result
    assert result.get("certification") == "NOT_GRANTED_BY_CRFU", result
    assert result.get("canonical_promotion") == "NOT_AUTHORIZED", result


if __name__ == "__main__":
    raise SystemExit(main())
