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
SCOPE = "VERIFY_REPAIR_PRIMITIVES_AND_BUILD_LOUKSNAPG_CANDIDATE"
WORKER_ID = "CUSTOSZV9"

REQUIRED_REPAIR_SOURCE_FRAGMENTS = (
    'query="phrase(sentence,[the,man,shoots]),write(true),halt"',
    r'use_module(library(dcgs)).\\n',
    r"include('{grammar_literal}').\\n",
    r"initialization(({query})).\\n",
    'trealla_env["TPL_LIBRARY_PATH"]=str(packaged_library)',
    "regex [c a t]:[g a t o];",
    'base + "/readyz"',
    '"rqlite_readiness": ready_receipt',
)
REQUIRED_REPAIR_REGRESSION_TESTS = (
    "test_trealla_probe_executes_packaged_binary_without_source_build",
    "test_foma_probe_executes_packaged_foma_and_flookup",
    "test_rqlite_readiness_requires_elected_leader_and_store",
    "test_rqlite_readiness_polls_readyz_not_status",
)


def repair_source_contract_failures(repair_source: str, repair_tests: str) -> list[str]:
    """Keep the source preflight aligned with the actual packaged Trealla driver."""
    missing = [fragment for fragment in REQUIRED_REPAIR_SOURCE_FRAGMENTS if fragment not in repair_source]
    missing.extend(
        "required_regression_test_missing:" + name
        for name in REQUIRED_REPAIR_REGRESSION_TESTS if name not in repair_tests
    )
    return missing


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
        and "REPAIR_SOURCE_HASHES_PINNED" in task.get("preconditions", [])
        and "REAL_CANDIDATE_PRIMITIVE_TESTS_REQUIRED" in task.get("preconditions", [])
        and "WRITE_EVIDENCE" in task.get("permitted_effects", [])
    )
    return {
        "status": "PASS" if valid else "FAIL",
        "task_id": task.get("task_id"),
        "authorizes_global_certification": False,
    }


def build_task(head: str, paths: dict[str, Path]) -> dict:
    contract_sha256 = sha256_file(paths["architecture_contract"])
    return {
        "task_id": TASK_ID,
        "mission_id": "issue-155",
        "project_id": "louksnapg",
        "source_identity": WORKER_ID,
        "target_identity": "LOUKSNAPG",
        "source_state_hash": sha256_bytes(head.encode("ascii")),
        "architecture_contract_sha256": contract_sha256,
        "dependency_set": ["issue-155"],
        "authorized_scope": SCOPE,
        "required_capabilities": ["verify_repair_primitives", "build_single_file_distribution"],
        "inputs": [
            str(paths["document"]),
            str(paths["runtime"]),
            str(paths["source_architecture"]),
            str(paths["cajita_doc"]),
            str(paths["architecture_contract"]),
        ],
        "preconditions": ["NO_SELF_CERTIFICATION", "FAIL_CLOSED", "INPUT_HASHES_VERIFIABLE", "REPAIR_SOURCE_HASHES_PINNED", "REAL_CANDIDATE_PRIMITIVE_TESTS_REQUIRED"],
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
            "output_within_479000000_bytes",
            "runtime_archive_within_470000000_bytes",
            "input_hashes_and_protected_prefix_preserved",
            "three_repaired_non_model_primitives_executed_on_exact_candidate_and_outcomes_bound",
            "candidate_bound_primitive_report_persisted",
        ],
        "expected_outputs": ["LOUKSNAPG.md", "LOUKSNAPG_BUILD_REPORT.json", "LOUKSNAPG_CUSTOSZV9_PRIMITIVE_REPAIR_EVIDENCE.json"],
        "validation_strategy": "SEPARATE_INDEPENDENT_ZIP_VERIFIER",
        "evidence_requirements": ["source_commit", "input_hashes", "output_sha256", "exact_size", "exit_code"],
        "checkpoint_reference": head,
        "rollback_strategy": "REMOVE_INCOMPLETE_CANDIDATE_AND_KEEP_SOURCE_INPUTS_IMMUTABLE",
        "completion_condition": "CANDIDATE_BUILT_AND_THREE_REPAIR_TARGET_OUTCOMES_BOUND; FAILURES_KEEP_G24_ON_HOLD",
        "escalation_condition": "REPAIR_PREFLIGHT_FAILURE_OR_INCOMPLETE_EVIDENCE_OR_BUILD_HASH_CAP_FAILURE; ANY_PRIMITIVE_FAILURE_REMAINS_A_RELEASE_BLOCKER",
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
    parser.add_argument("--architecture-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=479000000)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)

    repo = args.repo_root.resolve()
    paths = {
        "document": args.document.resolve(),
        "runtime": args.runtime.resolve(),
        "source_architecture": args.source_architecture.resolve(),
        "cajita_doc": args.cajita_doc.resolve(),
        "architecture_contract": args.architecture_contract.resolve(),
        "output": args.output.resolve(),
    }
    for key in ("document", "runtime", "source_architecture", "cajita_doc", "architecture_contract"):
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

    input_hashes = {key: sha256_file(paths[key]) for key in ("document", "runtime", "source_architecture", "cajita_doc", "architecture_contract")}
    expected_contract_sha = os.environ.get("LOUKSNAPG_CONTRACT_SHA256", "").strip()
    if expected_contract_sha and expected_contract_sha != input_hashes["architecture_contract"]:
        raise SystemExit("ARCHITECTURE_CONTRACT_SHA256_MISMATCH")
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
    primitive_report_path = paths["output"].with_name("LOUKSNAPG_CUSTOSZV9_PRIMITIVE_REPAIR_EVIDENCE.json")
    repair_manifest = {
        "schema": "LOUKSNAPG_CUSTOSZ_REPAIR_MANIFEST/1.0",
        "source_commit": head,
        "targets": [
            {"target_id": "D04_HERMENEUTICA_HG", "fault": "Trealla DCG probe did not import library(dcgs) and loaded the grammar after evaluating the query", "required_fix": "load bundled grammar first and explicitly import library(dcgs)"},
            {"target_id": "D04_TRADUCCION_LENGUAS_ANTIGUAS", "fault": "Foma validation fixture treated unspaced strings as character sequences; upstream treats them as multi-character symbols", "required_fix": "compile regex [c a t]:[g a t o]; and verify packaged flookup returns gato"},
            {"target_id": "D06_MIGRACION_PERSISTENCIA", "fault": "rqlite write raced Raft leader election because /status was mistaken for write readiness", "required_fix": "poll /readyz until node, leader and store are ready before writes"},
        ],
        "product_scope": "bounded primitive repair validation; does not claim full hermeneutics or an ancient-language lexicon",
        "heavy_model_weight_download_count": 0,
        "remote_commander_used": False,
        "global_certification": "NOT_GRANTED",
    }

    def runner(payload: dict) -> dict:
        repair_source = (repo / "tools" / "cajita_extended_target_e2e.py").read_text(encoding="utf-8")
        repair_tests = (repo / "tests" / "test_cajita_extended_target_e2e.py").read_text(encoding="utf-8")
        absent_fragments = repair_source_contract_failures(repair_source, repair_tests)
        repair_test_command = [
            sys.executable, "-m", "unittest", "discover", "-s", "tests",
            "-p", "test_cajita_extended_target_e2e.py", "-v",
        ]
        if absent_fragments:
            action_result.update({
                "repair_source_contract_status": "FAIL",
                "missing_repair_fragments": absent_fragments,
                "repair_source_sha256": sha256_bytes(repair_source.encode("utf-8")),
                "repair_test_source_sha256": sha256_bytes(repair_tests.encode("utf-8")),
                "architecture_contract_sha256": input_hashes["architecture_contract"],
            })
            return {"status": "FAIL", "result_state_hash": sha256_bytes(json.dumps(action_result, sort_keys=True).encode()), "reason": "REPAIR_SOURCE_PATCH_MISSING", "certification": "NOT_GRANTED"}
        py_compile = subprocess.run(
            [sys.executable, "-m", "py_compile", str(repo / "tools" / "cajita_extended_target_e2e.py"), str(repo / "tests" / "test_cajita_extended_target_e2e.py")],
            cwd=repo, env=os.environ.copy(), capture_output=True, text=True, timeout=90, check=False,
        )
        unit = subprocess.run(
            repair_test_command, cwd=repo, env=os.environ.copy(),
            capture_output=True, text=True, timeout=600, check=False,
        )
        action_result["repair_preflight"] = {
            "schema": "LOUKSNAPG_REPAIR_PREFLIGHT/1.0",
            "status": "PASS" if py_compile.returncode == 0 and unit.returncode == 0 else "FAIL",
            "source_sha256": sha256_bytes(repair_source.encode("utf-8")),
            "test_source_sha256": sha256_bytes(repair_tests.encode("utf-8")),
            "required_source_fragments_present": len(REQUIRED_REPAIR_SOURCE_FRAGMENTS),
            "py_compile_exit_code": py_compile.returncode,
            "unit_test_exit_code": unit.returncode,
            "unit_test_stdout_tail": unit.stdout[-8000:],
            "unit_test_stderr_tail": unit.stderr[-4000:],
            "synthetic_unit_fixtures": True,
            "synthetic_fixtures_used_as_product_proof": False,
        }
        if py_compile.returncode != 0 or unit.returncode != 0:
            action_result.update({
                "exit_code": 2,
                "architecture_contract_sha256": input_hashes["architecture_contract"],
                "reason": "REPAIR_PREFLIGHT_TEST_FAILED",
            })
            return {"status": "FAIL", "result_state_hash": sha256_bytes(json.dumps(action_result, sort_keys=True).encode()), "reason": "REPAIR_PREFLIGHT_TEST_FAILED", "certification": "NOT_GRANTED"}
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
            "architecture_contract_sha256": input_hashes["architecture_contract"],
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
        if not exact:
            action_result["repair_status"] = "HOLD_BUNDLE_HASH_SIZE_OR_CAP_MISMATCH"
            return {
                "status": "FAIL",
                "result_state_hash": sha256_bytes(json.dumps({"head": head, "action": action_result}, sort_keys=True).encode()),
                "bundle_sha256": digest,
                "bundle_bytes": size,
                "cap_bytes": args.max_bytes,
                "certification": "NOT_GRANTED",
                "reason": "OUTPUT_SIZE_OR_HASH_REPORT_MISMATCH",
            }

        # Independently extract and exercise the exact candidate created in this
        # worker action. This is real candidate-bound runtime evidence, not a
        # source-only selftest. The evaluator keeps every blocker visible.
        import tempfile
        validator_report_path = paths["output"].with_name("LOUKSNAPG_CUSTOSZV9_PRIMITIVE_VALIDATOR.json")
        extended_report_path = primitive_report_path
        with tempfile.TemporaryDirectory(prefix="louksnapg-custosz-runtime-") as temp:
            temp_root = Path(temp)
            extracted = temp_root / "runtime"
            validator_report = temp_root / "validator.json"
            validator_command = [
                sys.executable, str(repo / "tools" / "louksnapg_independent_validator.py"),
                "--bundle", str(paths["output"]), "--max-bytes", str(args.max_bytes),
                "--expected-source-commit", head, "--extract-to", str(extracted),
                "--report", str(validator_report),
            ]
            validator_proc = subprocess.run(
                validator_command, cwd=repo, env=os.environ.copy(),
                capture_output=True, text=True, timeout=600, check=False,
            )
            validator_obj = {}
            if validator_report.is_file() and not validator_report.is_symlink():
                try:
                    validator_obj = json.loads(validator_report.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    validator_obj = {}
            action_result["candidate_independent_validation"] = {
                "exit_code": validator_proc.returncode,
                "report_sha256": sha256_file(validator_report) if validator_report.is_file() else None,
                "container_integrity": validator_obj.get("container_integrity"),
                "runtime_member_integrity": validator_obj.get("runtime_member_integrity"),
                "identity_preservation_status": validator_obj.get("identity_preservation_status"),
                "bundle_sha256": validator_obj.get("bundle_sha256"),
                "bundle_bytes": validator_obj.get("bundle_bytes"),
                "source_commit": validator_obj.get("source_commit"),
                "stderr_tail": validator_proc.stderr[-3000:],
            }
            if (
                validator_proc.returncode != 0 or not extracted.is_dir()
                or validator_obj.get("container_integrity") != "PASS"
                or validator_obj.get("runtime_member_integrity") != "PASS"
                or validator_obj.get("source_commit") != head
                or validator_obj.get("bundle_sha256") != digest
            ):
                action_result["repair_status"] = "HOLD_CANDIDATE_INDEPENDENT_VALIDATION_FAILED"
                return {
                    "status": "FAIL",
                    "result_state_hash": sha256_bytes(json.dumps({"head": head, "action": action_result}, sort_keys=True).encode()),
                    "bundle_sha256": digest,
                    "certification": "NOT_GRANTED",
                    "reason": "CANDIDATE_INDEPENDENT_VALIDATION_FAILED",
                }
            extended_command = [
                sys.executable, str(repo / "tools" / "cajita_extended_target_e2e.py"),
                "--root", str(extracted), "--source-commit", head,
                "--bundle-sha256", digest,
                "--contract", str(paths["architecture_contract"]),
                "--report", str(extended_report_path),
                "--only-target", "D04_HERMENEUTICA_HG",
                "--only-target", "D04_TRADUCCION_LENGUAS_ANTIGUAS",
                "--only-target", "D06_MIGRACION_PERSISTENCIA",
            ]
            extended_proc = subprocess.run(
                extended_command, cwd=repo, env=os.environ.copy(),
                capture_output=True, text=True, timeout=2400, check=False,
            )
        extended_obj = {}
        if extended_report_path.is_file() and not extended_report_path.is_symlink():
            try:
                extended_obj = json.loads(extended_report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                extended_obj = {}
        targets = extended_obj.get("targets", []) if isinstance(extended_obj, dict) else []
        target_status = {row.get("target_id"): row.get("status") for row in targets if isinstance(row, dict)}
        repaired_target_ids = [
            "D04_HERMENEUTICA_HG", "D04_TRADUCCION_LENGUAS_ANTIGUAS", "D06_MIGRACION_PERSISTENCIA"
        ]
        repaired_pass = all(target_status.get(target_id) == "PASS_PRIMITIVE_SMOKE" for target_id in repaired_target_ids)
        exact_report_binding = (
            extended_obj.get("source_commit") == head
            and extended_obj.get("bundle_sha256") == digest
            and extended_obj.get("contract_sha256") == input_hashes["architecture_contract"]
            and extended_obj.get("coverage_execution") == "COMPLETE_DIAGNOSTIC_ONLY"
            and len(targets) == len(repaired_target_ids)
            and set(target_status) == set(repaired_target_ids)
            and (extended_obj.get("summary") or {}).get("all_target_outcomes_recorded") is True
        )
        action_result["primitive_repair_evidence"] = {
            "schema": "LOUKSNAPG_CUSTOSZ_PRIMITIVE_REPAIR_EVIDENCE/1.0",
            "status": "PASS" if extended_proc.returncode == 0 and exact_report_binding and repaired_pass else "HOLD",
            "report_path": extended_report_path.name,
            "report_sha256": sha256_file(extended_report_path) if extended_report_path.is_file() else None,
            "repair_source_sha256": (action_result.get("repair_preflight") or {}).get("source_sha256"),
            "repair_test_source_sha256": (action_result.get("repair_preflight") or {}).get("test_source_sha256"),
            "exit_code": extended_proc.returncode,
            "source_commit": extended_obj.get("source_commit"),
            "bundle_sha256": extended_obj.get("bundle_sha256"),
            "contract_sha256": extended_obj.get("contract_sha256"),
            "target_count": len(targets),
            "target_status": target_status,
            "targeted_repairs": repaired_target_ids,
            "targeted_repairs_all_pass": repaired_pass,
            "all_target_outcomes_recorded": exact_report_binding,
            "summary": extended_obj.get("summary"),
            "stdout_tail": extended_proc.stdout[-5000:],
            "stderr_tail": extended_proc.stderr[-3000:],
            "heavy_model_weight_download_count": 0,
            "remote_commander_used": False,
            "synthetic_evidence_used_as_product_proof": False,
            "global_certification": "NOT_GRANTED",
        }
        # Worker completion means the bounded repair verification actually ran
        # against the exact candidate and recorded a complete result set. A
        # FAIL/BLOCKED primitive is not rewritten as PASS: it remains in the
        # report and keeps the separate G24 release gate on HOLD.
        task_executed = (
            extended_proc.returncode == 0 and exact_report_binding
            and extended_obj.get("heavy_model_weight_download_count") == 0
            and extended_obj.get("remote_commander_used") is False
            and extended_obj.get("synthetic_evidence_used_as_product_proof") is False
        )
        state = sha256_bytes(json.dumps({"head": head, "bundle_sha256": digest, "size": size, "primitive_report_sha256": action_result["primitive_repair_evidence"].get("report_sha256")}, sort_keys=True).encode())
        action_result["repair_status"] = "PASS_THREE_TARGETED_PRIMITIVES" if repaired_pass else "HOLD_REPAIR_BLOCKERS_RECORDED"
        action_result["exit_code"] = 0 if task_executed else 2
        action_result["primitive_report_sha256"] = action_result["primitive_repair_evidence"].get("report_sha256")
        return {
            "status": "PASS" if task_executed else "FAIL",
            "result_state_hash": state,
            "bundle_sha256": digest,
            "bundle_bytes": size,
            "cap_bytes": args.max_bytes,
            "repair_status": action_result["repair_status"],
            "primitive_report_sha256": action_result["primitive_report_sha256"],
            "certification": "NOT_GRANTED",
            "reason": "" if task_executed else "PRIMITIVE_REPAIR_REPORT_INCOMPLETE_OR_SAFETY_BINDING_FAILED",
        }

    outcome = run_bounded_mission(
        task,
        [ActionSpec(
            "verify_repair_primitives_and_build_single_file_distribution",
            required_capabilities=("verify_repair_primitives", "build_single_file_distribution"),
            permitted_effects=("WRITE_EVIDENCE",),
            idempotency="IDEMPOTENT",
        )],
        snapshot,
        available_capabilities={"verify_repair_primitives", "build_single_file_distribution"},
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
        and build_report.get("identity_preservation_status") == "PASS_SOURCE_IDENTITY_PRESERVED"
        and build_report.get("engine_replacement") == "FORBIDDEN"
        and action_result.get("architecture_contract_sha256") == input_hashes["architecture_contract"]
        and action_result.get("primitive_repair_evidence", {}).get("all_target_outcomes_recorded") is True
        and action_result.get("primitive_repair_evidence", {}).get("status") == "PASS"
        and action_result.get("primitive_repair_evidence", {}).get("targeted_repairs_all_pass") is True
        and action_result.get("repair_status") == "PASS_THREE_TARGETED_PRIMITIVES"
        and action_result.get("repair_preflight", {}).get("status") == "PASS"
    )
    # CUSTOSZ's coordinator uses COMPLETED for a successful bounded mission.
    # The build action's return code plus the exact independent-report binding
    # determines whether the worker job succeeded; the coordinator status alone
    # is not a product certification.
    worker_status = "PASS" if action_succeeded else "FAIL"
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "").strip()
    workflow_url = (
        os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
        + "/" + os.environ.get("GITHUB_REPOSITORY", "").strip("/")
        + "/actions/runs/" + run_id
    ) if run_id else None
    report = {
        "schema": "LOUKSNAPG_CUSTOSZV9_WORKER_EVIDENCE/1.0",
        "generated_at_utc": utc_now(),
        "worker_run_id": run_id or None,
        "worker_job_id": os.environ.get("GITHUB_JOB"),
        "worker_run_attempt": run_attempt or None,
        "workflow_url": workflow_url,
        "source_commit": head,
        "contract_sha256": input_hashes["architecture_contract"],
        "architecture_contract_sha256": input_hashes["architecture_contract"],
        "bundle_sha256": output_hash,
        "worker": WORKER_ID,
        "worker_contract_role": "CUSTOSZ_V9",
        "worker_sha256": worker_hash,
        "mission_id": "issue-155",
        "task_id": TASK_ID,
        "authorized_scope": SCOPE,
        "worker_status": worker_status,
        "coordinator_status": coordinator_status,
        "worker_outcome": outcome,
        "repair_mission": {
            "schema": "LOUKSNAPG_CUSTOSZ_REPAIR_MISSION_RECEIPT/1.0",
            "mission_id": "issue-155",
            "task_id": TASK_ID,
            "worker_id": WORKER_ID,
            "authorized_scope": SCOPE,
            "status": action_result.get("repair_status", "NOT_EXECUTED"),
            "primitive_evidence_schema": "LOUKSNAPG_CUSTOSZ_PRIMITIVE_REPAIR_EVIDENCE/1.0",
            "repair_preflight_status": (action_result.get("repair_preflight") or {}).get("status", "NOT_EXECUTED"),
            "candidate_integrity_status": "PASS" if (action_result.get("candidate_independent_validation") or {}).get("container_integrity") == "PASS" and (action_result.get("candidate_independent_validation") or {}).get("runtime_member_integrity") == "PASS" else "HOLD",
            "primitive_report_hash_verified": bool((action_result.get("primitive_repair_evidence") or {}).get("report_sha256")) and (action_result.get("primitive_report_sha256") == (action_result.get("primitive_repair_evidence") or {}).get("report_sha256")),
            "source_commit": head,
            "contract_sha256": input_hashes["architecture_contract"],
            "bundle_sha256": output_hash,
            "repair_source_sha256": (action_result.get("repair_preflight") or {}).get("source_sha256"),
            "repair_test_source_sha256": (action_result.get("repair_preflight") or {}).get("test_source_sha256"),
            "primitive_report_sha256": (action_result.get("primitive_repair_evidence") or {}).get("report_sha256"),
            "target_results": (action_result.get("primitive_repair_evidence") or {}).get("target_status", {}),
            "all_target_outcomes_recorded": (action_result.get("primitive_repair_evidence") or {}).get("all_target_outcomes_recorded") is True,
            "targeted_repairs_all_pass": (action_result.get("primitive_repair_evidence") or {}).get("targeted_repairs_all_pass") is True,
            "heavy_model_weight_download_count": 0,
            "remote_commander_used": False,
            "synthetic_unit_fixtures_used_as_product_proof": False,
            "global_certification": "NOT_GRANTED",
        },
        "action_success_criteria": {
            "action_exit_code_zero": action_result.get("exit_code") == 0,
            "artifact_exists": output_exists,
            "within_cap": bool(output_size is not None and output_size <= args.max_bytes),
            "build_report_size_matches": build_report.get("bundle_bytes") == output_size,
            "build_report_hash_matches": build_report.get("bundle_sha256") == output_hash,
            "build_report_source_commit_matches": build_report.get("source_commit") == head,
            "identity_preservation_pass": build_report.get("identity_preservation_status") == "PASS_SOURCE_IDENTITY_PRESERVED",
            "engine_replacement_forbidden": build_report.get("engine_replacement") == "FORBIDDEN",
            "architecture_contract_binding_pass": action_result.get("architecture_contract_sha256") == input_hashes["architecture_contract"],
            "repair_preflight_tests_pass": action_result.get("repair_preflight", {}).get("status") == "PASS",
            "candidate_primitive_report_present": bool(action_result.get("primitive_repair_evidence", {}).get("report_sha256")),
            "targeted_primitives_pass": action_result.get("primitive_repair_evidence", {}).get("targeted_repairs_all_pass") is True,
            "repair_status": action_result.get("repair_status"),
        },
        "input_sha256": input_hashes,
        "action": action_result,
        "repair_manifest": repair_manifest,
        "repair_status": action_result.get("repair_status", "NOT_EXECUTED"),
        "primitive_repair_report": action_result.get("primitive_repair_evidence"),
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
