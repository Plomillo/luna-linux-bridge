#!/usr/bin/env python3
"""Structural source/model conformance checks for CUSTOSZ V9's normalized contracts.

This is not a universal Python-to-Agda refinement proof. It fails closed when
source-level contract anchors or the finite mission-state transition graph drift.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GATES = {
    "custoszv9/crfu/resources.py": (
        "evaluate_budget",
        ("RAM_BUDGET_EXCEEDED", "DISK_BUDGET_EXCEEDED", "CONCURRENCY_BUDGET_INVALID",
         "RESOURCE_MEASUREMENT_NOT_TRUSTED", "RESOURCE_MEASUREMENT_INVALID"),
    ),
    "custoszv9/crfu/planner.py": (
        "build_plan",
        ("DEPENDENCY_UNRESOLVED", "ACTION_NOT_ADMISSIBLE", "DEPENDENCY_CYCLE", "PLAN_VALIDATED"),
    ),
    "custoszv9/crfu/recovery.py": (
        "verify_restoration",
        ("RESTORED_BYTES_MISMATCH", "RESTORED_STATE_IDENTITY_MISMATCH",
         "RESTORED_DEPENDENCY_MISMATCH", "RESTORED_INVARIANTS_NOT_PROVEN", "EVIDENCE_JOURNAL_INVALID"),
    ),
    "custoszv9/crfu/formal.py": (
        "validate_proof_bundle",
        ("PROOF_TARGET_IDENTITY_MISMATCH", "PROOF_SCOPE_MISMATCH", "FORMAL_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED"),
    ),
}
QUEUE_SOURCE = "custoszv9/crfu/event_queue.py"
QUEUE_MODEL = "formal/crfu/MissionQueueSemantics.agda"
PLANNER_MODEL = "formal/crfu/PlannerDecisionSemantics.agda"
RECOVERY_MODEL = "formal/crfu/RecoveryDecisionSemantics.agda"
EQUIVALENCE_MODEL = "formal/crfu/EquivalenceDecisionSemantics.agda"
JOURNAL_MODEL = "formal/crfu/JournalChainSemantics.agda"
RESOURCE_MODEL = "formal/crfu/ResourceBudgetDecisionSemantics.agda"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
EDGE_RE = re.compile(r"^\s*([a-z][a-z0-9-]*)\s*:\s*([A-Z_]+)\s*↝\s*([A-Z_]+)\s*$")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def function_node(tree: ast.AST, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise ValueError("FUNCTION_NOT_FOUND:" + name)


def node_text(node: ast.AST) -> str:
    return ast.unparse(node)


def read_source(root: Path, relative: str) -> tuple[str, str]:
    path = root / relative
    if not path.is_file():
        raise ValueError("SOURCE_MISSING:" + relative)
    raw = path.read_bytes()
    return raw.decode("utf-8"), sha(raw)


def check_queue_graph(root: Path) -> dict[str, Any]:
    source, source_sha = read_source(root, QUEUE_SOURCE)
    model, model_sha = read_source(root, QUEUE_MODEL)
    tree = ast.parse(source, filename=QUEUE_SOURCE)
    allowed_node = next((n for n in tree.body if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == "ALLOWED" for t in n.targets)), None)
    if allowed_node is None:
        raise ValueError("QUEUE_ALLOWED_TRANSITION_TABLE_MISSING")
    runtime = ast.literal_eval(allowed_node.value)
    if not isinstance(runtime, dict) or not all(isinstance(k, str) and isinstance(v, (set, frozenset)) for k, v in runtime.items()):
        raise ValueError("QUEUE_ALLOWED_TABLE_SHAPE_INVALID")
    runtime_edges = {(source_state, target_state) for source_state, targets in runtime.items() for target_state in targets}
    model_edges = set()
    for line in model.splitlines():
        match = EDGE_RE.match(line)
        if match:
            model_edges.add((match.group(2), match.group(3)))
    if runtime_edges != model_edges:
        missing_model = sorted(runtime_edges - model_edges)
        extra_model = sorted(model_edges - runtime_edges)
        raise ValueError("QUEUE_TRANSITION_GRAPH_DRIFT:" + json.dumps({
            "runtime_edges_missing_from_agda": missing_model,
            "agda_edges_not_in_runtime": extra_model,
        }, sort_keys=True))
    terminal = {"COMPLETED", "FAILED", "BLOCKED", "DENIED"}
    for state in terminal:
        if runtime.get(state, set()):
            raise ValueError("RUNTIME_TERMINAL_STATE_HAS_OUTGOING:" + state)
    for state in ("COMPLETED", "FAILED", "BLOCKED", "DENIED"):
        theorem = state.lower() + "-has-no-outgoing-transition"
        if theorem not in model:
            raise ValueError("FORMAL_TERMINAL_INVARIANT_MISSING:" + theorem)
    return {
        "contract": "MISSION_QUEUE_FINITE_TRANSITION_GRAPH",
        "result": "PASS",
        "runtime_sha256": source_sha,
        "formal_sha256": model_sha,
        "runtime_edge_count": len(runtime_edges),
        "formal_edge_count": len(model_edges),
        "comparison": "EXACT_FINITE_EDGE_SET",
    }


def validate(root: Path, candidate_sha: str) -> dict[str, Any]:
    failures: list[str] = []
    results: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}

    for relative, (name, markers) in GATES.items():
        try:
            text, digest = read_source(root, relative)
            hashes[relative] = digest
            tree = ast.parse(text, filename=relative)
            fn = function_node(tree, name)
            function_source = node_text(fn)
            missing = [marker for marker in markers if marker not in text]
            if missing:
                raise ValueError("REQUIRED_RUNTIME_GUARD_MISSING:" + ",".join(missing))
            results.append({
                "contract": name,
                "runtime_path": relative,
                "runtime_sha256": digest,
                "runtime_function_ast_sha256": sha(function_source.encode("utf-8")),
                "result": "PASS",
                "method": "AST_PARSE_AND_REQUIRED_GUARD_ANCHORS",
                "missing_guards": [],
            })
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as exc:
            failures.append(relative + ":" + str(exc))
            results.append({"contract": name, "runtime_path": relative, "result": "FAIL", "reason": str(exc)})

    try:
        resource_text, resource_sha = read_source(root, "custoszv9/crfu/resources.py")
        budget_fn = function_node(ast.parse(resource_text), "evaluate_budget")
        budget_ast = node_text(budget_fn)
        required_exprs = (
            "budget.ram_required_bytes + budget.ram_reserved_bytes >= snapshot.ram_available_bytes",
            "budget.disk_required_bytes >= snapshot.disk_available_bytes",
            "RESOURCE_MEASUREMENT_INVALID",
        )
        missing = [expr for expr in required_exprs if expr not in budget_ast]
        if missing:
            raise ValueError("STRICT_RESOURCE_SEMANTICS_MISMATCH:" + ",".join(missing))
        formal_resource, formal_sha = read_source(root, RESOURCE_MODEL)
        for marker in ("ramRequired b + ramReserved b < ramAvailable b", "diskRequired b < diskAvailable b"):
            if marker not in formal_resource:
                raise ValueError("FORMAL_RESOURCE_GUARD_MISSING:" + marker)
        results.append({
            "contract": "RESOURCE_BUDGET_STRICT_BOUNDARIES",
            "runtime_sha256": resource_sha,
            "formal_sha256": formal_sha,
            "result": "PASS",
            "method": "AST_GUARD_BINDING",
            "claim_limit": "structural source conformance, not a universal semantic-refinement theorem",
        })
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as exc:
        failures.append("RESOURCE_BUDGET_STRICT_BOUNDARIES:" + str(exc))

    try:
        results.append(check_queue_graph(root))
        hashes[QUEUE_SOURCE] = sha((root / QUEUE_SOURCE).read_bytes())
        hashes[QUEUE_MODEL] = sha((root / QUEUE_MODEL).read_bytes())
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as exc:
        failures.append("MISSION_QUEUE_FINITE_TRANSITION_GRAPH:" + str(exc))

    formal_expectations = {
        PLANNER_MODEL: ("plannerDecision", "validated-plan-never-authorizes-execution", "dependencyGraphAcyclic"),
        RECOVERY_MODEL: ("restorationDecision", "pass-requires-valid-journal", "payloadBytesMatch"),
        EQUIVALENCE_MODEL: ("equivalenceDecision", "all-equivalence-guards-imply-admissible", "forbiddenPropertyAbsent"),
        JOURNAL_MODEL: ("journalValid", "journal-pass-implies-all-links-match", "wrong-event-digest-blocks-journal"),
        RESOURCE_MODEL: ("budgetDecision", "budget-pass-requires-valid-budget", "ramWithinBudget"),
    }
    for relative, markers in formal_expectations.items():
        try:
            text, digest = read_source(root, relative)
            hashes[relative] = digest
            missing = [marker for marker in markers if marker not in text]
            if missing:
                raise ValueError("FORMAL_GUARD_OR_THEOREM_MISSING:" + ",".join(missing))
            results.append({
                "contract": relative.rsplit("/", 1)[-1],
                "formal_sha256": digest,
                "result": "PASS",
                "method": "REQUIRED_MODEL_AND_THEOREM_ANCHORS",
                "claim_limit": "checks presence and source identity, not universal Python semantics",
            })
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            failures.append(relative + ":" + str(exc))
            results.append({"contract": relative, "result": "FAIL", "reason": str(exc)})

    status = "FAIL" if failures else "PASS_STRUCTURAL_SOURCE_CONFORMANCE"
    payload = {
        "schema": "CUSTOSZV9_SOURCE_CONTRACT_CONFORMANCE/1.0",
        "candidate_sha": candidate_sha,
        "result": status,
        "universal_refinement_proven": False,
        "method_limit": "AST guard binding, required formal theorem anchors, and exhaustive finite queue-edge equality; not an execution-semantics proof for arbitrary Python/SQLite behavior.",
        "source_sha256": dict(sorted(hashes.items())),
        "contracts": results,
        "failures": sorted(set(failures)),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    payload["report_sha256"] = sha(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.root.resolve(), args.candidate_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate_sha": report["candidate_sha"],
        "result": report["result"],
        "failures": report["failures"],
        "report_sha256": report["report_sha256"],
    }, sort_keys=True))
    return 1 if report["result"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
