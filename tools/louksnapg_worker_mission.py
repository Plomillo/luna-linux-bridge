#!/usr/bin/env python3
"""Run the LOUKSNAPG bundle build through the pinned CUSTOSZ V9 worker.

CUSTOSZ V9 coordinates the authorized, bounded build action. The worker cannot
grant global certification; the output is only a candidate until the independent
integrity and functional gates separately pass.
"""
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
TASK_ID = "louksnapg-integral-release"
SCOPE = "BUILD_LOUKSNAPG_SINGLE_FILE_CANDIDATE"
WORKER_ID = "CUSTOSZV9"


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
    return {
        "task_id": TASK_ID,
        "mission_id": "issue-155",
        "project_id": "louksnapg",
        "source_identity": WORKER_ID,
        "target_identity": "LOUKSNAPG",
        "source_state_hash": sha256_bytes(head.encode("ascii")),
        "dependency_set": ["issue-155"],
        "authorized_scope": SCOPE,
        "required_capabilities": ["build_single_file_distribution"],
        "inputs": [
            str(paths["document"]),
            str(paths["runtime"]),
            str(paths["source_architecture"]),
            str(paths["cajita_doc"]),
        ],
        "preconditions": ["NO_SELF_CERTIFICATION", "FAIL_CLOSED", "INPUT_HASHES_VERIFIABLE"],
        "permitted_effects": ["WRITE_EVIDENCE"],
        "resource_budget": {
            "ram_required_bytes": 128 * 1024 * 1024,
            "ram_reserved_bytes": 64 * 1024 * 1024,
            "disk_required_bytes": 512 * 1024 * 1024,
            "max_concurrency": 1,
        },
        "execution_deadline": "2026-12-31T23:59:59Z",
        "maximum_planning_budget": 4,
        "maximum_retry_budget": 0,
        "acceptance_criteria": [
            "output_is_single_LOUKSNAPG_md_container",
            "output_within_470000000_bytes",
            "input_hashes_and_protected_prefix_preserved",
        ],
        "expected_outputs": ["LOUKSNAPG.md", "LOUKSNAPG_BUILD_REPORT.json"],
        "validation_strategy": "SEPARATE_INDEPENDENT_ZIP_VERIFIER",
        "evidence_requirements": ["source_commit", "input_hashes", "output_sha256", "exact_size", "exit_code"],
        "checkpoint_reference": head,
        "rollback_strategy": "REMOVE_INCOMPLETE_CANDIDATE_AND_KEEP_SOURCE_INPUTS_IMMUTABLE",
        "completion_condition": "CANDIDATE_BUILT_AND_EXACT_SIZE_MEASURED",
        "escalation_condition": "BUILD_ERROR_OR_ANY_INPUT_HASH_OR_CAP_CHECK_FAILURE",
        "authorization_evidence_reference": "https://github.com/Plomillo/luna-linux-bridge/issues/155",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--source-architecture", type=Path, required=True)
    parser.add_argument("--cajita-doc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=470000000)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)

    repo = args.repo_root.resolve()
    paths = {
        "document": args.document.resolve(),
        "runtime": args.runtime.resolve(),
        "source_architecture": args.source_architecture.resolve(),
        "cajita_doc": args.cajita_doc.resolve(),
        "output": args.output.resolve(),
    }
    for key in ("document", "runtime", "source_architecture", "cajita_doc"):
        path = paths[key]
        if path.is_symlink() or not path.is_file():
            raise SystemExit("REQUIRED_INPUT_NOT_REGULAR_FILE:" + key + ":" + str(path))
    # The output is an expected build product, not a prerequisite. Refuse to
    # overwrite a pre-existing candidate so each worker run starts cleanly.
    if paths["output"].exists() or paths["output"].is_symlink():
        raise SystemExit("OUTPUT_CANDIDATE_ALREADY_EXISTS_FAIL_CLOSED:" + str(paths["output"]))
    head = os.environ.get("GITHUB_SHA", "").strip()
    if len(head) != 40 or any(ch not in "0123456789abcdef" for ch in head):
        raise SystemExit("GITHUB_SHA_MISSING_OR_INVALID")

    input_hashes = {key: sha256_file(paths[key]) for key in ("document", "runtime", "source_architecture", "cajita_doc")}
    run_bounded_mission, ActionSpec, probe_host_resources, worker_hash = load_worker(args.worker.resolve())
    task = build_task(head, paths)
    snapshot = probe_host_resources(repo)
    command = [
        sys.executable, str(repo / "tools" / "louksnapg_bundle.py"),
        "--document", str(paths["document"]),
        "--runtime", str(paths["runtime"]),
        "--source-architecture", str(paths["source_architecture"]),
        "--cajita-doc", str(paths["cajita_doc"]),
        "--output", str(paths["output"]),
        "--max-bytes", str(args.max_bytes),
    ]
    action_result: dict = {}

    def runner(payload: dict) -> dict:
        proc = subprocess.run(
            command,
            cwd=repo,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
        action_result.update({
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-6000:],
            "stderr_tail": proc.stderr[-4000:],
            "command_sha256": sha256_bytes(json.dumps(command, separators=(",", ":")).encode()),
        })
        if proc.returncode != 0 or not paths["output"].is_file():
            return {
                "status": "FAIL",
                "result_state_hash": sha256_bytes(json.dumps(action_result, sort_keys=True).encode()),
                "reason": "BUNDLE_BUILD_FAILED",
                "certification": "NOT_GRANTED",
            }
        size = paths["output"].stat().st_size
        digest = sha256_file(paths["output"])
        report_path = paths["output"].with_name("LOUKSNAPG_BUILD_REPORT.json")
        report_obj = json.loads(report_path.read_text(encoding="utf-8"))
        exact = size <= args.max_bytes and report_obj.get("bundle_sha256") == digest and report_obj.get("bundle_bytes") == size
        state = sha256_bytes(json.dumps({"head": head, "bundle_sha256": digest, "size": size}, sort_keys=True).encode())
        return {
            "status": "PASS" if exact else "FAIL",
            "result_state_hash": state,
            "bundle_sha256": digest,
            "bundle_bytes": size,
            "cap_bytes": args.max_bytes,
            "certification": "NOT_GRANTED",
            "reason": "" if exact else "OUTPUT_SIZE_OR_HASH_REPORT_MISMATCH",
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
    output_exists = paths["output"].is_file()
    output_size = paths["output"].stat().st_size if output_exists else None
    output_hash = sha256_file(paths["output"]) if output_exists else None
    build_report_path = paths["output"].with_name("LOUKSNAPG_BUILD_REPORT.json")
    build_report = {}
    if build_report_path.is_file() and not build_report_path.is_symlink():
        try:
            build_report = json.loads(build_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            build_report = {}
    action_succeeded = (
        coordinator_status in {"PASS", "COMPLETED"}
        and action_result.get("exit_code") == 0
        and output_exists
        and output_size is not None
        and output_size <= args.max_bytes
        and build_report.get("bundle_bytes") == output_size
        and build_report.get("bundle_sha256") == output_hash
        and build_report.get("source_commit") == head
    )
    # CUSTOSZ's coordinator uses COMPLETED for a successful bounded mission.
    # The build action's return code plus the exact independent-report binding
    # determines whether the worker job succeeded; the coordinator status alone
    # is not a product certification.
    worker_status = "PASS" if action_succeeded else "FAIL"
    report = {
        "schema": "LOUKSNAPG_CUSTOSZV9_WORKER_EVIDENCE/1.0",
        "generated_at_utc": utc_now(),
        "source_commit": head,
        "worker": WORKER_ID,
        "worker_sha256": worker_hash,
        "mission_id": "issue-155",
        "task_id": TASK_ID,
        "authorized_scope": SCOPE,
        "worker_status": worker_status,
        "coordinator_status": coordinator_status,
        "worker_outcome": outcome,
        "action_success_criteria": {
            "action_exit_code_zero": action_result.get("exit_code") == 0,
            "artifact_exists": output_exists,
            "within_cap": bool(output_size is not None and output_size <= args.max_bytes),
            "build_report_size_matches": build_report.get("bundle_bytes") == output_size,
            "build_report_hash_matches": build_report.get("bundle_sha256") == output_hash,
            "build_report_source_commit_matches": build_report.get("source_commit") == head,
        },
        "input_sha256": input_hashes,
        "action": action_result,
        "artifact": {
            "path": paths["output"].name,
            "exists": output_exists,
            "bytes": output_size,
            "sha256": output_hash,
            "cap_bytes": args.max_bytes,
            "within_cap": bool(output_size is not None and output_size <= args.max_bytes),
        },
        "global_certification": "NOT_GRANTED",
        "authority": "BOUNDED_WORKER_NOT_INDEPENDENT_CERTIFIER",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": worker_status,
        "coordinator_status": coordinator_status,
        "worker": WORKER_ID,
        "artifact": paths["output"].name,
        "bytes": output_size,
        "sha256": output_hash,
        "global_certification": "NOT_GRANTED",
    }, ensure_ascii=False, indent=2))
    return 0 if worker_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
