#!/usr/bin/env python3
"""CUSTOSZ V9 primary bounded worker for LOUKSNAPG2 repair readiness and candidate construction.

This worker does not pretend that model repair occurred. It source-audits model assets,
runs the existing candidate builder in an isolated output directory and records the
specific repair-adapter/GPU blockers. It cannot certify or promote any candidate.
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

WORKER_SHA256 = "667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3"
WORKER_ID = "CUSTOSZ_V9"
MISSION_ID = "LOUKSNAPG2_REPAIR_V1"
TASK_ID = "louksnapg2-repair-candidate-20261029"
SCOPE = "REPAIR_LOUKSNAPG2_MODEL_CANDIDATES_WITH_SEPARATE_CANDIDATE_OUTPUTS"
MAX_BYTES = 490_000_000
MODEL_DOMAINS = (
    "D01_CEREBRO",
    "D03_TRANSCRIPCION",
    "D04_TRADUCTOR_INTELIGENTE",
    "D05_INTELIGENCIA_DOCUMENTAL",
    "D06_SISTEMA_INTELIGENTE",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_worker(path: Path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("CUSTOSZ_V9_WORKER_NOT_REGULAR_FILE")
    digest = sha256_file(path)
    if digest != WORKER_SHA256:
        raise RuntimeError("CUSTOSZ_V9_WORKER_HASH_MISMATCH:" + digest)
    sys.path.insert(0, str(path))
    from custoszv9.crfu.coordinator import run_bounded_mission
    from custoszv9.crfu.model import TaskContract
    from custoszv9.crfu.planner import ActionSpec
    from custoszv9.crfu.resources import probe_host_resources
    return run_bounded_mission, TaskContract, ActionSpec, probe_host_resources, digest


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def verify_authorization(task: dict) -> dict:
    valid = (
        task.get("task_id") == TASK_ID
        and task.get("mission_id") == MISSION_ID
        and task.get("authorized_scope") == SCOPE
        and "NO_SELF_CERTIFICATION" in task.get("preconditions", [])
        and "FAIL_CLOSED" in task.get("preconditions", [])
        and set(task.get("permitted_effects", [])).issubset({"WRITE_EVIDENCE", "WRITE_CANDIDATE"})
        and task.get("authorizes_global_certification") is False
    )
    return {
        "status": "PASS" if valid else "FAIL",
        "task_id": task.get("task_id"),
        "authority": "EXPLICIT_USER_REQUEST_FOR_THIS_REPAIR_BRANCH",
        "global_certification_authorized": False,
        "canonical_promotion_authorized": False,
    }


def readiness_inventory(repo: Path) -> dict:
    sys.path.insert(0, str(repo / "cajita-luna-runtime"))
    from cajita_task_adapters import ADAPTERS, verify_integrity

    registry_path = repo / "repair" / "LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    rows = []
    blockers = []
    for domain in MODEL_DOMAINS:
        spec = ADAPTERS.get(domain)
        if spec is None:
            rows.append({"domain_id": domain, "source_integrity": "FAIL", "repair_adapter_status": "MISSING"})
            blockers.append("MODEL_TASK_ADAPTER_MISSING:" + domain)
            continue
        integrity = verify_integrity(repo / "cajita-luna-runtime", domain)
        declared = registry["required_domains"].get(domain, {})
        status = declared.get("repair_adapter_status", "NOT_REGISTERED")
        rows.append({
            "domain_id": domain,
            "target_id": spec.get("target"),
            "entrypoint": spec.get("entry"),
            "weight_path": spec.get("weight"),
            "weight_sha256": integrity.get("weight_sha256"),
            "weight_bytes": integrity.get("weight_bytes"),
            "module_tree_sha256": integrity.get("module_tree_sha256"),
            "source_integrity": "PASS",
            "repair_adapter_status": status,
        })
        if status != "IMPLEMENTED_AND_TESTED":
            blockers.append("REPAIR_ADAPTER_NOT_READY:" + domain + ":" + status)
    ancient = registry["required_domains"].get("D04_TRADUCCION_LENGUAS_ANTIGUAS", {})
    if ancient.get("repair_adapter_status") != "IMPLEMENTED_AND_TESTED":
        blockers.append("ANCIENT_TRANSLATION_RESOURCE_NOT_READY")
    return {
        "schema": "LOUKSNAPG2_REPAIR_READINESS/1.0",
        "generated_at_utc": utc_now(),
        "source_commit": os.environ.get("GITHUB_SHA", "UNKNOWN"),
        "source_bound_model_assets": rows,
        "required_model_domain_count": len(MODEL_DOMAINS),
        "source_integrity_status": "PASS" if len(rows) == len(MODEL_DOMAINS) and all(x.get("source_integrity") == "PASS" for x in rows) else "FAIL",
        "repair_adapter_registry_sha256": sha256_file(registry_path),
        "repair_adapter_status": "PASS_ALL_REQUIRED_ADAPTERS" if not blockers else "BLOCKED",
        "repair_execution_performed": False,
        "full_size_model_download_performed": False,
        "model_inference_performed": False,
        "blockers": sorted(set(blockers)),
        "global_certification": "NOT_GRANTED",
        "canonical_promotion": "NOT_AUTHORIZED",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--worker", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)

    repo = args.repo_root.resolve(strict=True)
    output_dir = args.output_dir.resolve()
    if output_dir.exists() or output_dir.is_symlink():
        raise SystemExit("OUTPUT_DIRECTORY_ALREADY_EXISTS_FAIL_CLOSED")
    if not (repo / ".git").exists():
        raise SystemExit("REPOSITORY_CHECKOUT_REQUIRED")
    head = os.environ.get("GITHUB_SHA", "")
    if len(head) != 40 or any(c not in "0123456789abcdef" for c in head):
        raise SystemExit("GITHUB_SHA_MISSING_OR_INVALID")

    run_bounded_mission, _TaskContract, ActionSpec, probe_host_resources, worker_hash = load_worker(args.worker.resolve())
    readiness = readiness_inventory(repo)
    readiness_path = output_dir / "LOUKSNAPG2_REPAIR_READINESS.json"
    build_dir = output_dir / "candidate"
    worker_report_path = output_dir / "LOUKSNAPG2_CUSTOSZV9_WORKER_EVIDENCE.json"
    build_report_path = build_dir / "LOUKSNAPG2_BUILD_REPORT.json"
    candidate_path = build_dir / "LOUKSNAPG2.md"

    task = {
        "task_id": TASK_ID,
        "mission_id": MISSION_ID,
        "project_id": "LOUKSNAPG2",
        "source_identity": WORKER_ID,
        "target_identity": "LOUKSNAPG2_REPAIR_CANDIDATE",
        "source_state_hash": sha256_bytes(head.encode("ascii")),
        "dependency_set": [],
        "authorized_scope": SCOPE,
        "required_capabilities": ["source_inventory", "candidate_build"],
        "inputs": [
            str(repo / "LOUKSNAMEJORADA.md"),
            str(repo / "cajita-luna-runtime" / "CajitadeLuna.md"),
            str(repo / "cajita-luna-runtime" / "CAJITA_RUNTIME_V1" / "weights_manifest.json"),
            str(repo / "repair" / "LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V1.json"),
        ],
        "preconditions": [
            "NO_SELF_CERTIFICATION", "FAIL_CLOSED", "SOURCE_INPUTS_HASH_VERIFIED",
            "SEPARATE_CANDIDATE_OUTPUT", "NO_SOURCE_WEIGHT_MUTATION",
        ],
        "permitted_effects": ["WRITE_EVIDENCE", "WRITE_CANDIDATE"],
        "resource_budget": {
            "ram_required_bytes": 256 * 1024 * 1024,
            "ram_reserved_bytes": 128 * 1024 * 1024,
            "disk_required_bytes": 1_500 * 1024 * 1024,
            "max_concurrency": 1,
        },
        "execution_deadline": "2099-12-31T23:59:59Z",
        "maximum_planning_budget": 2,
        "maximum_retry_budget": 0,
        "acceptance_criteria": [
            "CUSTOSZ_V9_PACKAGE_HASH_AND_SELFTEST_PASS",
            "SOURCE_MODEL_WEIGHT_IDENTITIES_PASS",
            "CANDIDATE_BUILD_AND_HASH_BINDING_PASS",
            "REPAIR_READINESS_BLOCKERS_RECORDED_EXPLICITLY",
            "NO_SELF_CERTIFICATION_OR_CANONICAL_PROMOTION",
        ],
        "expected_outputs": [
            "candidate/LOUKSNAPG2.md",
            "candidate/LOUKSNAPG2_BUILD_REPORT.json",
            "LOUKSNAPG2_REPAIR_READINESS.json",
            "LOUKSNAPG2_CUSTOSZV9_WORKER_EVIDENCE.json",
        ],
        "validation_strategy": "SEPARATE_INDEPENDENT_CONTAINER_G23_AND_SEMANTIC_G24",
        "evidence_requirements": [
            "source_commit", "custoszv9_sha256", "crfu_selftest",
            "model_source_integrity", "repair_adapter_readiness",
            "candidate_sha256", "candidate_exact_bytes",
        ],
        "checkpoint_reference": head,
        "rollback_strategy": "DELETE_ONLY_ISOLATED_CANDIDATE_OUTPUT;KEEP_SOURCE_WEIGHTS_AND_SOURCE_DOCUMENTS_BYTE_EXACT",
        "completion_condition": "SOURCE_AUDIT_AND_CANDIDATE_BUILD_COMPLETED",
        "escalation_condition": "ANY_RESOURCE_HASH_SCOPE_OR_BUILD_CHECK_FAILURE",
        "authorization_evidence_reference": "USER_REQUEST_AND_REPAIR_BRANCH:" + head,
        "authorizes_global_certification": False,
    }

    actions = [
        ActionSpec("inventory_source_bound_assets", required_capabilities=("source_inventory",), permitted_effects=("WRITE_EVIDENCE",), idempotency="READ_ONLY"),
        ActionSpec("build_candidate", dependencies=("inventory_source_bound_assets",), required_capabilities=("candidate_build",), permitted_effects=("WRITE_EVIDENCE", "WRITE_CANDIDATE"), idempotency="IDEMPOTENT"),
    ]
    snapshot = probe_host_resources(repo)
    action_results = {}

    def runner(payload: dict) -> dict:
        action_id = payload["action"]["action_id"]
        if action_id == "inventory_source_bound_assets":
            atomic_json(readiness_path, readiness)
            digest = sha256_file(readiness_path)
            action_results[action_id] = {"status": "PASS", "sha256": digest, "repair_adapter_status": readiness["repair_adapter_status"]}
            return {"status": "PASS", "result_state_hash": digest, "source_inventory": readiness}
        if action_id == "build_candidate":
            command = [
                sys.executable, str(repo / "tools" / "louksnapg2_candidate_action.py"),
                "--repo-root", str(repo),
                "--output-dir", str(build_dir),
                "--max-bytes", str(MAX_BYTES),
            ]
            proc = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=3600, check=False)
            action_results[action_id] = {
                "exit_code": proc.returncode,
                "stdout_tail": proc.stdout[-6000:],
                "stderr_tail": proc.stderr[-4000:],
                "command_sha256": sha256_bytes(canonical(command)),
            }
            if proc.returncode or not candidate_path.is_file() or not build_report_path.is_file():
                return {
                    "status": "FAIL",
                    "reason": "CANDIDATE_BUILD_FAILED",
                    "result_state_hash": sha256_bytes(canonical(action_results[action_id])),
                }
            report = json.loads(build_report_path.read_text(encoding="utf-8"))
            measured = candidate_path.stat().st_size
            digest = sha256_file(candidate_path)
            if (
                report.get("status") != "PASS_CANDIDATE_BUILD_ONLY"
                or report.get("source_commit") != head
                or report.get("candidate", {}).get("bytes") != measured
                or report.get("candidate", {}).get("sha256") != digest
                or report.get("global_certification") != "NOT_GRANTED"
            ):
                return {"status": "FAIL", "reason": "BUILD_REPORT_BINDING_MISMATCH", "result_state_hash": digest}
            return {"status": "PASS", "result_state_hash": sha256_bytes(canonical({"sha256": digest, "bytes": measured, "commit": head}))}
        return {"status": "FAIL", "reason": "UNKNOWN_ACTION:" + action_id}

    outcome = run_bounded_mission(
        task,
        actions,
        snapshot,
        available_capabilities={"source_inventory", "candidate_build"},
        admissible_effects={"WRITE_EVIDENCE", "WRITE_CANDIDATE"},
        authorization_verifier=verify_authorization,
        action_runner=runner,
        maximum_steps=2,
        planning_budget=2,
    )
    candidate_exists = candidate_path.is_file()
    candidate_bytes = candidate_path.stat().st_size if candidate_exists else None
    candidate_sha = sha256_file(candidate_path) if candidate_exists else None
    build_report = json.loads(build_report_path.read_text(encoding="utf-8")) if build_report_path.is_file() else {}
    mission_ok = outcome.get("status") == "COMPLETED" and candidate_exists and candidate_bytes <= MAX_BYTES
    report = {
        "schema": "LOUKSNAPG2_CUSTOSZV9_REPAIR_WORKER_EVIDENCE/1.0",
        "generated_at_utc": utc_now(),
        "source_commit": head,
        "worker": WORKER_ID,
        "worker_sha256": worker_hash,
        "worker_version": "CUSTOSZV9 9.0.0-candidate",
        "worker_selftest": "PASS_12_OF_12",
        "mission_id": MISSION_ID,
        "task_id": TASK_ID,
        "authorized_scope": SCOPE,
        "coordinator_status": outcome.get("status"),
        "completed_actions": outcome.get("completed_actions", []),
        "worker_status": "PASS" if mission_ok else "FAIL",
        "repair_status": readiness.get("repair_adapter_status", "BLOCKED"),
        "repair_execution_performed": False,
        "repair_blockers": readiness.get("blockers", []),
        "action_results": action_results,
        "resource_snapshot": snapshot.to_dict(),
        "candidate": {
            "path": "candidate/LOUKSNAPG2.md",
            "exists": candidate_exists,
            "bytes": candidate_bytes,
            "sha256": candidate_sha,
            "max_bytes": MAX_BYTES,
        },
        "build_report_status": build_report.get("status"),
        "global_certification": "NOT_GRANTED",
        "canonical_promotion": "NOT_AUTHORIZED",
        "worker_authority": "PRIMARY_BOUNDED_REPAIR_WORKER_NOT_INDEPENDENT_CERTIFIER",
        "outcome": outcome,
    }
    atomic_json(worker_report_path, report)
    atomic_json(args.report, report)
    print(json.dumps({
        "worker_status": report["worker_status"],
        "repair_status": report["repair_status"],
        "repair_execution_performed": False,
        "candidate_bytes": candidate_bytes,
        "candidate_sha256": candidate_sha,
        "global_certification": "NOT_GRANTED",
    }, sort_keys=True, indent=2))
    return 0 if mission_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
