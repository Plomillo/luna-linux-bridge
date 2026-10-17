#!/usr/bin/env python3
"""Bind exact Agda and Python source revisions for bounded resource-rule evidence.

This checker validates source bindings and selected guards; it is not a universal
refinement prover and cannot issue a package or canonical Louksna certificate.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

FORMAL_COMMIT = "e8fb3f83f97e3577cbac77aa369eaccc425317b1"
RUNTIME_COMMIT = "62d2d649b47f7653f3c9e9d1eeb42e563371053a"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def require_contains(path: Path, fragments: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise SystemExit(f"SOURCE_GUARD_BINDING_FAILED:{path}:{missing!r}")


def main() -> int:
    root = Path.cwd()
    formal = root / "formal-src"
    runtime = root / "runtime-src"
    actual_formal = git_head(formal)
    actual_runtime = git_head(runtime)
    workspace_commit = git_head(root)
    if actual_formal != FORMAL_COMMIT:
        raise SystemExit(f"FORMAL_COMMIT_MISMATCH:{actual_formal}")
    if actual_runtime != RUNTIME_COMMIT:
        raise SystemExit(f"RUNTIME_COMMIT_MISMATCH:{actual_runtime}")

    # Prove the candidate PR has not changed the exact runtime implementation
    # or the bounded test file relative to the source revision being evaluated.
    for relative in ("custoszv9/crfu/resources.py", "tests/test_custoszv9.py"):
        workspace_file = root / relative
        pinned_file = runtime / relative
        if sha256(workspace_file) != sha256(pinned_file):
            raise SystemExit(f"WORKSPACE_RUNTIME_BYTES_CHANGED:{relative}")

    py = runtime / "custoszv9/crfu/resources.py"
    agda_runtime = formal / "formal/crfu/ResourceBudgetRuntimeSemantics.agda"
    agda_decision = formal / "formal/crfu/ResourceBudgetDecisionSemantics.agda"
    agda_proofs = formal / "formal/crfu/ResourceBudgetRuntimeSemanticsProofs.agda"
    test_file = runtime / "tests/test_custoszv9.py"

    require_contains(py, [
        "def _nonnegative_int(value: object) -> bool:",
        "return isinstance(value, int) and not isinstance(value, bool) and value >= 0",
        "if budget.ram_required_bytes + budget.ram_reserved_bytes >= snapshot.ram_available_bytes:",
        'fail.append("RAM_BUDGET_EXCEEDED")',
        "if budget.disk_required_bytes >= snapshot.disk_available_bytes:",
        'fail.append("DISK_BUDGET_EXCEEDED")',
    ])
    require_contains(agda_runtime, [
        "ResourceNeed.requiredRam r + ResourceNeed.reservedRam r < ResourceNeed.availableRam r",
        "ResourceNeed.requiredDisk r < ResourceNeed.availableDisk r",
    ])
    require_contains(agda_decision, [
        "ramWithinBudget b = ramRequired b + ramReserved b < ramAvailable b",
        "diskWithinBudget b = diskRequired b < diskAvailable b",
        "concurrencyWithinBudget b =",
        "budgetDecision : BudgetInput -> BudgetDecision",
    ])
    require_contains(agda_proofs, [
        "ram-reservation-at-or-above-availability-is-rejected",
        "disk-equality-at-available-capacity-is-rejected",
        "legacy-strict-ram-model-agrees-at-equality",
        "legacy-strict-disk-model-agrees-at-equality",
    ])
    require_contains(test_file, [
        "def test_runtime_resource_decision_matches_formal_predicates_on_bounded_domain(self):",
        "self.assertEqual(checked, 4**7)",
    ])

    files = [py, agda_runtime, agda_decision, agda_proofs, test_file]
    report = {
        "schema": "CUSTOSZV9_BOUNDED_MODEL_RUNTIME_BINDING/1.0",
        "status": "SOURCE_BINDINGS_VALIDATED_PENDING_TYPECHECK_AND_RUNTIME_TESTS",
        "workspace_commit": workspace_commit,
        "formal_commit": actual_formal,
        "runtime_commit": actual_runtime,
        "runtime_bytes_match_workspace": True,
        "scope": "STRICT_RAM_AND_DISK_RESOURCE_ADMISSION_PREDICATES_AND_BOUNDED_DIFFERENTIAL_REGRESSION",
        "bindings": [
            {
                "runtime_rule": "required_ram + reserved_ram < available_ram",
                "python_impl": "RAM guard rejects required + reserved >= available",
                "agda_model": "requiredRam + reservedRam < availableRam",
                "status": "SOURCE_EXPRESSION_BOUND",
            },
            {
                "runtime_rule": "required_disk < available_disk",
                "python_impl": "disk guard rejects required >= available",
                "agda_model": "requiredDisk < availableDisk",
                "status": "SOURCE_EXPRESSION_BOUND",
            },
            {
                "runtime_rule": "budget input integers are nonnegative and bool is excluded",
                "python_impl": "_nonnegative_int rejects bool and negative values",
                "agda_model": "Agda fields are Nat and budgetFieldsValid is an abstract input predicate",
                "status": "PARTIAL_MODEL_ABSTRACTION_EXPLICIT",
            },
        ],
        "source_files": [
            {
                "path": str(path.relative_to(root)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
        "limits": [
            "This binds inspected source expressions at exact commits; it does not prove all Python/SQLite executions refine the Agda model.",
            "A 4**7 bounded test is finite regression evidence, not a universal theorem.",
            "The Agda validity flag abstracts Python type, nullability, confidence, and evidence-source handling.",
            "It issues no G22/G23/G24 certificate, package certification, global G01-G24 certification, activation, or canonical promotion.",
        ],
    }
    out = root / "evidence/custoszv9-bounded-model-runtime-binding.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
