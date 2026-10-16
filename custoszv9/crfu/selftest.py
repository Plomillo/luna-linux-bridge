"""Bounded, offline CRFU conformance, stress, integrity and recovery tests."""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .anti_paralysis import decide_next_action, state_fingerprint
from .equivalence import validate_equivalence
from .event_queue import PersistentMissionQueue
from .evidence import append_event, verify_journal
from .formal import validate_proof_bundle
from .model import sha256_bytes
from .planner import ActionSpec, build_plan
from .puac2 import validate_claim_v2
from .recovery import checkpoint_record, verify_restoration
from .resources import ResourceBudget, ResourceSnapshot, evaluate_budget


def _task(index: int) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "task_id": f"selftest-{index:04d}",
        "mission_id": f"selftest-{index:04d}",
        "project_id": "crfu-offline-selftest",
        "source_identity": "selftest-source",
        "target_identity": "selftest-target",
        "source_state_hash": sha256_bytes(b"selftest-source-state"),
        "dependency_set": [],
        "authorized_scope": "LOCAL_TEST_ONLY",
        "required_capabilities": [],
        "inputs": {},
        "preconditions": [],
        "permitted_effects": [],
        "resource_budget": {
            "ram_required_bytes": 0,
            "ram_reserved_bytes": 0,
            "disk_required_bytes": 0,
            "max_concurrency": 1,
        },
        "execution_deadline": (now + timedelta(minutes=5)).isoformat(),
        "maximum_planning_budget": 1,
        "maximum_retry_budget": 0,
        "acceptance_criteria": [],
        "expected_outputs": [],
        "validation_strategy": "offline-selftest",
        "evidence_requirements": [],
        "checkpoint_reference": None,
        "rollback_strategy": "temporary-file-checkpoint-restore",
        "completion_condition": "selftest complete",
        "escalation_condition": "deny on failed invariant",
        "authorization_evidence_reference": "TEST_FIXTURE_NOT_AUTHORIZATION",
    }


def run_selftest() -> dict:
    checks: dict[str, bool] = {}

    plan = build_plan(
        [ActionSpec("b", ("a",)), ActionSpec("a")],
        max_alternatives=4,
        available_capabilities=set(),
        admissible_effects=set(),
    )
    checks["deterministic_topological_plan"] = (
        plan["status"] == "PLAN_VALIDATED" and plan["ordered_actions"] == ["a", "b"]
        and plan.get("execution_authorized") is False
    )
    cycle = build_plan(
        [ActionSpec("a", ("b",)), ActionSpec("b", ("a",))],
        max_alternatives=4,
        available_capabilities=set(),
        admissible_effects=set(),
    )
    checks["dependency_cycle_denied"] = cycle["status"] == "DENIED"

    # A bounded O(n^2) planner stress case; no external process or side effects.
    stress_ids = [f"task-{i:04d}" for i in range(256)]
    stress_actions = [
        ActionSpec(item, () if i == 0 else (stress_ids[i - 1],))
        for i, item in enumerate(stress_ids)
    ]
    stress = build_plan(
        stress_actions,
        max_alternatives=256,
        available_capabilities=set(),
        admissible_effects=set(),
    )
    checks["bounded_256_action_stress"] = (
        stress["status"] == "PLAN_VALIDATED"
        and stress["ordered_actions"] == stress_ids
        and stress.get("execution_authorized") is False
    )

    budget = evaluate_budget(
        ResourceBudget(1, 1, 0, 1),
        ResourceSnapshot(None, None, None, "2026-01-01T00:00:00Z", "selftest", "UNKNOWN"),
    )
    checks["unknown_resources_hold"] = budget["status"] == "HOLD"

    fingerprint = state_fingerprint({"phase": 1})
    retry = decide_next_action(
        action_id="a",
        strategy_id="s",
        state_hash=fingerprint,
        previous_attempts=[{"action_id": "a", "strategy_id": "s", "state_hash": fingerprint}],
        new_evidence=False,
        planning_budget_remaining=1,
        retry_budget_remaining=0,
    )
    checks["repeated_strategy_without_evidence_blocked"] = retry["decision"] == "BLOCKED"

    with tempfile.TemporaryDirectory(prefix="custoszv9-selftest-") as td:
        base = Path(td)
        journal_path = base / "journal.jsonl"
        event = {
            "operation_id": "o",
            "mission_id": "m",
            "sequence_id": 1,
            "timestamp_utc": "2026-01-01T00:00:00Z",
            "actor": "selftest",
            "tool_and_version": "crfu-selftest/2",
            "source_identity": "test",
            "input_hash_and_size": {"sha256": sha256_bytes(b"i"), "size_bytes": 1},
            "output_hash_and_size": {"sha256": sha256_bytes(b"o"), "size_bytes": 1},
            "validation_result": "PASS",
            "authorization_evidence_reference": "TEST_FIXTURE_NOT_AUTHORIZATION",
            "dependency_context": [],
            "rollback_pointer": None,
            "status": "TEST_ONLY",
        }
        append_event(journal_path, event)
        checks["journal_chain_valid"] = verify_journal(journal_path)["status"] == "PASS"
        journal_path.write_text(
            journal_path.read_text(encoding="utf-8").replace(
                '"status":"TEST_ONLY"', '"status":"TAMPERED"'
            ),
            encoding="utf-8",
        )
        checks["journal_tamper_detected"] = verify_journal(journal_path)["status"] == "FAIL"

        # Exercise the actual checkpoint/restore validator on isolated temporary files.
        before = b"checkpoint state before mutation"
        dependency_hash = sha256_bytes(b"dependency fingerprint")
        checkpoint = checkpoint_record(
            before,
            checkpoint_id="selftest-checkpoint",
            state_identity="selftest-state-v1",
            dependency_fingerprint=dependency_hash,
        )
        checkpoint_file = base / "checkpoint.bin"
        target_file = base / "target.bin"
        checkpoint_file.write_bytes(before)
        target_file.write_bytes(before)
        target_file.write_bytes(b"mutated state")
        target_file.write_bytes(checkpoint_file.read_bytes())
        restored = target_file.read_bytes()
        result = verify_restoration(
            checkpoint,
            restored,
            expected_state_identity="selftest-state-v1",
            expected_dependency_fingerprint=dependency_hash,
            invariants_pass=True,
            journal_valid=True,
        )
        checks["offline_checkpoint_restore_postvalidated"] = (
            result["status"] == "PASS"
            and result["restoration_proven"] is True
            and sha256_bytes(restored) == sha256_bytes(before)
            and result["certification_propagation"] is False
        )

        # Bound and verify event-driven queue behavior; no polling thread or host effects.
        queue = PersistentMissionQueue(base / "missions.sqlite3")
        queue_ok = True
        expected_missions = {f"selftest-{i:04d}" for i in range(32)}
        try:
            for i in range(32):
                accepted = queue.submit(_task(i))
                if accepted.get("state") != "RECEIVED":
                    queue_ok = False
            for mission in sorted(expected_missions):
                queue.transition(
                    mission, "RECEIVED", "PREFLIGHT", event_type="SELFTEST_PREFLIGHT"
                )
                queue.transition(
                    mission, "PREFLIGHT", "READY", event_type="SELFTEST_READY"
                )
            claimed = set()
            while True:
                item = queue.claim_next_ready()
                if item is None:
                    break
                claimed.add(item["mission_id"])
                queue.transition(
                    item["mission_id"], "RUNNING", "COMPLETED",
                    event_type="SELFTEST_COMPLETE",
                )
            chain = queue.verify_event_chain()
            queue_ok = queue_ok and claimed == expected_missions
            queue_ok = queue_ok and chain.get("status") == "PASS"
            queue_ok = queue_ok and chain.get("event_count") == 160
        except Exception:
            queue_ok = False
        checks["bounded_queue_32_missions_and_hash_chain"] = queue_ok

    equivalence = validate_equivalence({
        "source_sha256": "a" * 64,
        "target_sha256": "b" * 64,
        "equivalence_specification_id": "SELFTEST_SCOPE",
        "specification_sha256": "c" * 64,
        "proof_status": "VERIFIED",
        "proof_verified_by": "independent-test-validator",
        "producer_identity": "candidate-producer",
        "transportable_properties": ["certification"],
    })
    checks["equivalence_cannot_transport_certification"] = (
        equivalence["status"] == "UNPROVEN"
        and equivalence["property_transport"] == "DENIED"
    )

    proof = validate_proof_bundle({}, "a" * 64, "CRFU_SELFTEST")
    checks["missing_formal_proof_fails_closed"] = proof["status"] == "HOLD"

    now = datetime.now(timezone.utc)
    claim = {
        "claim_id": "selftest-claim",
        "subject_id": "selftest-subject",
        "property_id": "selftest-property",
        "scope_id": "LOCAL_TEST_ONLY",
        "context_id": "selftest-context",
        "version": "1",
        "validity_interval": {
            "not_before_utc": (now - timedelta(minutes=1)).isoformat(),
            "expires_at_utc": (now + timedelta(hours=1)).isoformat(),
        },
        "unit_of_measure": {"unit_id": "count", "dimension": "count", "version": "1"},
        "value": 1,
        "evidence_state": "UNKNOWN",
    }
    claim_result = validate_claim_v2(claim)
    checks["puac_claim_schema_does_not_assert_truth"] = (
        claim_result["status"] == "PASS_SCHEMA_ONLY"
        and claim_result.get("claim_truth_asserted") is False
    )

    failed = sorted(key for key, value in checks.items() if not value)
    return {
        "schema": "CUSTOSZV9_CRFU_SELFTEST/2.0",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "check_count": len(checks),
        "failed_checks": failed,
        "external_host_operations": False,
        "authorization_granted": False,
        "certification": "NOT_GRANTED_BY_SELFTEST",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_selftest(), ensure_ascii=False, sort_keys=True, indent=2))
