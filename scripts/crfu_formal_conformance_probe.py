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
from typing import Callable


IMPLEMENTATION_PATHS = [
    "custoszv9/__init__.py",
    "custoszv9/crfu/__init__.py",
    "custoszv9/crfu/model.py",
    "custoszv9/crfu/planner.py",
    "custoszv9/crfu/resources.py",
    "custoszv9/crfu/recovery.py",
    "custoszv9/crfu/equivalence.py",
    "custoszv9/crfu/formal.py",
    "custoszv9/crfu/gates.py",
    "custoszv9/crfu/puac2.py",
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
    from custoszv9.crfu.equivalence import validate_equivalence
    from custoszv9.crfu.formal import validate_proof_bundle
    from custoszv9.crfu.gates import evaluate_gate_evidence
    from custoszv9.crfu.planner import ActionSpec, build_plan
    from custoszv9.crfu.recovery import checkpoint_record, verify_restoration
    from custoszv9.crfu.resources import ResourceBudget, ResourceSnapshot, evaluate_budget

    observations: list[dict[str, str]] = []

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
            expected_reason="RAM_AVAILABLE_UNKNOWN",
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
            "runtime_symbols": [],
            "coverage": "NOT_MAPPED_TO_A_UNIQUE_RUNTIME_COMPOSITION_THEOREM",
            "boundary": "No exact one-to-one runtime composition theorem is established in this probe.",
        },
        {
            "formal_module": "MigrationCoherence.agda",
            "runtime_symbols": [],
            "coverage": "NOT_MAPPED_TO_A_UNIQUE_RUNTIME_MIGRATION_THEOREM",
            "boundary": "Recovery probes do not constitute a migration-coherence proof.",
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
            "runtime_symbols": [],
            "coverage": "NOT_PROVEN_DIRECT_REFINEMENT",
            "boundary": "No direct refinement theorem to the SQLite mission queue is established by this probe.",
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


def _assert_gate_hold(result):
    assert result.get("status") == "HOLD", result
    assert result.get("release_eligible") is False, result
    assert result.get("certification") == "NOT_GRANTED_BY_CRFU", result
    assert result.get("canonical_promotion") == "NOT_AUTHORIZED", result


if __name__ == "__main__":
    raise SystemExit(main())
