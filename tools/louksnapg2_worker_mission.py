#!/usr/bin/env python3
"""Execute LOUKSNAPG2 construction via the source-pinned CUSTOSZ V9 worker."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CUSTOSZ_SHA256 = "d585b351f617f4d5d134248e0c427d36ee0172b7ec32b0bdef6b7d381d394817"
TASK_ID = "louksnapg2-integral-release"
SCOPE = "BUILD_LOUKSNAPG2_SINGLE_FILE_CANDIDATE"
WORKER_ID = "CUSTOSZV9"
MAX_BYTES = 490_000_000


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_worker(worker_pyz: Path):
    if worker_pyz.is_symlink() or not worker_pyz.is_file():
        raise RuntimeError("CUSTOSZ_V9_WORKER_NOT_REGULAR_FILE")
    actual = sha256_file(worker_pyz)
    if actual != CUSTOSZ_SHA256:
        raise RuntimeError("CUSTOSZ_V9_WORKER_HASH_MISMATCH:" + actual)
    sys.path.insert(0, str(worker_pyz))
    from custoszv9.crfu.coordinator import run_bounded_mission
    from custoszv9.crfu.model import TaskContract
    from custoszv9.crfu.planner import ActionSpec
    from custoszv9.crfu.resources import probe_host_resources
    if not isinstance(getattr(TaskContract, "source_state_hash", None), property):
        TaskContract.source_state_hash = property(lambda self: str(self.value["source_state_hash"]))
    return run_bounded_mission, ActionSpec, probe_host_resources, actual


def authorize(task: dict) -> dict:
    valid = (
        task.get("task_id") == TASK_ID
        and task.get("mission_id") == "issue-159"
        and task.get("authorized_scope") == SCOPE
        and "NO_SELF_CERTIFICATION" in task.get("preconditions", [])
        and "FAIL_CLOSED" in task.get("preconditions", [])
        and "WRITE_EVIDENCE" in task.get("permitted_effects", [])
    )
    return {
        "status": "PASS" if valid else "FAIL",
        "task_id": task.get("task_id"),
        "authorizes_global_certification": False,
    }


def build_task(head: str, paths: dict[str, Path]) -> dict:
    input_names = (
        "source_architecture", "cajita_doc", "engine", "model_loader",
        "route_overlay", "externalized_assets", "candidate_action",
    )
    return {
        "task_id": TASK_ID,
        "mission_id": "issue-159",
        "project_id": "louksnapg2",
        "source_identity": WORKER_ID,
        "target_identity": "LOUKSNAPG2",
        "source_state_hash": sha256_bytes(head.encode("ascii")),
        "dependency_set": ["issue-159"],
        "authorized_scope": SCOPE,
        "required_capabilities": ["build_single_file_distribution"],
        "inputs": [str(paths[key]) for key in input_names],
        "preconditions": [
            "NO_SELF_CERTIFICATION", "FAIL_CLOSED", "INPUT_HASHES_VERIFIABLE",
            "PROTECTED_ARCHITECTURE_FROZEN", "ORIGINAL_CAJITA_TREE_PRESERVED",
        ],
        "permitted_effects": ["WRITE_EVIDENCE"],
        "resource_budget": {
            "ram_required_bytes": 512 * 1024 * 1024,
            "ram_reserved_bytes": 256 * 1024 * 1024,
            "disk_required_bytes": 1_500 * 1024 * 1024,
            "max_concurrency": 1,
        },
        "execution_deadline": "2026-12-31T23:59:59Z",
        "maximum_planning_budget": 4,
        "maximum_retry_budget": 0,
        "acceptance_criteria": [
            "single_file_Louksna_improved_plus_Cajita_candidate",
            "candidate_bytes_at_most_490000000",
            "exact_architecture_prefix_and_Cajita_document_suffix",
            "runtime_member_hashes_and_independent_container_validation_pass",
            "no_global_certification_claim_from_worker",
        ],
        "expected_outputs": ["LOUKSNAPG2.md", "LOUKSNAPG2_BUILD_REPORT.json"],
        "validation_strategy": "SEPARATE_INDEPENDENT_ZIP_VERIFIER_AND_REAL_MODEL_FUNCTIONAL_GATE",
        "evidence_requirements": [
            "source_commit", "all_source_input_hashes", "output_sha256",
            "exact_output_size", "candidate_cap", "independent_integrity_verdict",
        ],
        "checkpoint_reference": head,
        "rollback_strategy": "REMOVE_INCOMPLETE_CANDIDATE_AND_KEEP_SOURCE_INPUTS_IMMUTABLE",
        "completion_condition": "CANDIDATE_BUILT_AND_EXACT_SIZE_MEASURED",
        "escalation_condition": "BUILD_ERROR_OR_ANY_INPUT_HASH_OR_CAP_CHECK_FAILURE",
        "authorization_evidence_reference": "https://github.com/Plomillo/luna-linux-bridge/issues/159",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.max_bytes != MAX_BYTES:
        raise SystemExit("ALTERNATIVE_BUDGET_CHANGE_NOT_AUTHORIZED")

    repo = args.repo_root.resolve(strict=True)
    output_dir = args.output_dir.resolve()
    runtime = repo / "cajita-luna-runtime" / "LOUKSNAPG2_RUNTIME"
    paths = {
        "source_architecture": repo / "LOUKSNAMEJORADA.md",
        "cajita_doc": repo / "cajita-luna-runtime" / "CajitadeLuna.md",
        "engine": runtime / "louksnapg2_engine.py",
        "model_loader": runtime / "louksnapg2_model_loader.py",
        "route_overlay": runtime / "route_overlay.json",
        "externalized_assets": runtime / "externalized_assets.json",
        "candidate_action": repo / "tools" / "louksnapg2_candidate_action.py",
    }
    for key, path in paths.items():
        if path.is_symlink() or not path.is_file():
            raise SystemExit("REQUIRED_INPUT_NOT_REGULAR_FILE:" + key)
    if output_dir.exists() or output_dir.is_symlink():
        raise SystemExit("OUTPUT_DIRECTORY_ALREADY_EXISTS_FAIL_CLOSED")

    head = os.environ.get("GITHUB_SHA", "").strip()
    if len(head) != 40 or any(ch not in "0123456789abcdef" for ch in head):
        raise SystemExit("GITHUB_SHA_MISSING_OR_INVALID")
    input_hashes = {key: sha256_file(path) for key, path in paths.items()}
    run_bounded_mission, ActionSpec, probe_host_resources, worker_hash = load_worker(args.worker.resolve())
    task = build_task(head, paths)
    snapshot = probe_host_resources(repo)
    candidate_path = output_dir / "LOUKSNAPG2.md"
    build_report_path = output_dir / "LOUKSNAPG2_BUILD_REPORT.json"
    command = [
        sys.executable, str(repo / "tools" / "louksnapg2_candidate_action.py"),
        "--repo-root", str(repo), "--output-dir", str(output_dir),
        "--max-bytes", str(args.max_bytes),
    ]
    action_result: dict = {}

    def runner(payload: dict) -> dict:
        proc = subprocess.run(
            command, cwd=repo, env=os.environ.copy(), capture_output=True,
            text=True, timeout=3600, check=False,
        )
        action_result.update({
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-8000:],
            "stderr_tail": proc.stderr[-5000:],
            "command_sha256": sha256_bytes(json.dumps(command, separators=(",", ":")).encode()),
        })
        if proc.returncode != 0 or not candidate_path.is_file() or not build_report_path.is_file():
            return {
                "status": "FAIL",
                "result_state_hash": sha256_bytes(json.dumps(action_result, sort_keys=True).encode()),
                "reason": "LOUKSNAPG2_CANDIDATE_ACTION_FAILED",
                "certification": "NOT_GRANTED",
            }
        report_obj = json.loads(build_report_path.read_text(encoding="utf-8"))
        size = candidate_path.stat().st_size
        digest = sha256_file(candidate_path)
        expected = report_obj.get("candidate", {})
        exact = (
            report_obj.get("status") == "PASS_CANDIDATE_BUILD_ONLY"
            and size <= args.max_bytes
            and expected.get("bytes") == size
            and expected.get("sha256") == digest
            and report_obj.get("source_commit") == head
            and report_obj.get("global_certification") == "NOT_GRANTED"
            and report_obj.get("independent_validation", {}).get("identity_preservation_status") == "PASS_SOURCE_IDENTITY_PRESERVED"
        )
        state = sha256_bytes(json.dumps({"head": head, "bundle_sha256": digest, "size": size}, sort_keys=True).encode())
        return {
            "status": "PASS" if exact else "FAIL",
            "result_state_hash": state,
            "bundle_sha256": digest,
            "bundle_bytes": size,
            "cap_bytes": args.max_bytes,
            "certification": "NOT_GRANTED",
            "reason": "" if exact else "OUTPUT_SIZE_SOURCE_OR_VALIDATOR_REPORT_MISMATCH",
        }

    outcome = run_bounded_mission(
        task,
        [ActionSpec(
            "build_single_file_distribution",
            required_capabilities=("build_single_file_distribution",),
            permitted_effects=("WRITE_EVIDENCE",),
            idempotency="IDEMPOTENT",
        )],
        snapshot,
        available_capabilities={"build_single_file_distribution"},
        admissible_effects={"WRITE_EVIDENCE"},
        authorization_verifier=authorize,
        action_runner=runner,
        maximum_steps=1,
        planning_budget=4,
    )
    coordinator_status = outcome.get("status", "UNKNOWN")
    output_exists = candidate_path.is_file() and not candidate_path.is_symlink()
    output_size = candidate_path.stat().st_size if output_exists else None
    output_hash = sha256_file(candidate_path) if output_exists else None
    build_report = {}
    if build_report_path.is_file() and not build_report_path.is_symlink():
        try:
            build_report = json.loads(build_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            build_report = {}
    worker_status = "PASS" if (
        coordinator_status in {"PASS", "COMPLETED"}
        and action_result.get("exit_code") == 0
        and output_exists and output_size is not None and output_size <= args.max_bytes
        and build_report.get("candidate", {}).get("bytes") == output_size
        and build_report.get("candidate", {}).get("sha256") == output_hash
        and build_report.get("source_commit") == head
        and build_report.get("global_certification") == "NOT_GRANTED"
    ) else "FAIL"
    report = {
        "schema": "LOUKSNAPG2_CUSTOSZV9_WORKER_EVIDENCE/1.0",
        "generated_at_utc": utc_now(),
        "source_commit": head,
        "worker": WORKER_ID,
        "worker_sha256": worker_hash,
        "mission_id": "issue-159",
        "task_id": TASK_ID,
        "authorized_scope": SCOPE,
        "worker_status": worker_status,
        "coordinator_status": coordinator_status,
        "worker_outcome": outcome,
        "input_sha256": input_hashes,
        "action": action_result,
        "artifact": {
            "path": candidate_path.name,
            "exists": output_exists,
            "bytes": output_size,
            "sha256": output_hash,
            "cap_bytes": args.max_bytes,
            "within_cap": bool(output_size is not None and output_size <= args.max_bytes),
        },
        "global_certification": "NOT_GRANTED",
        "authority": "CUSTOSZV9_BOUNDED_BUILDER_NOT_INDEPENDENT_CERTIFIER",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": worker_status,
        "coordinator_status": coordinator_status,
        "worker": WORKER_ID,
        "artifact": candidate_path.name,
        "bytes": output_size,
        "sha256": output_hash,
        "global_certification": "NOT_GRANTED",
    }, ensure_ascii=False, indent=2))
    return 0 if worker_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
