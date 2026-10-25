#!/usr/bin/env python3
"""Sequential, fail-closed local startup controller for Cajita PUAC-2.

The controller performs read-only Blocks 1-3, records hash-chained telemetry outside
Cajita, and refuses to start transformation workers unless CUSTOSZ V9's own
authorization is active and the exact quantitative plan passes all preconditions.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import resource
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MIB = 1024 * 1024
GIB = 1024 * MIB
RAM_BUDGET_BYTES = GIB
CONTROLLER_AS_BYTES = 384 * MIB
CHILD_AS_BYTES = 640 * MIB
CHILD_TIMEOUT_SECONDS = 15
POLL_SECONDS = 0.10
MAX_LOG_BYTES = 1 * MIB

DEFAULT_CAJITA = Path(
    "/home/diegoignacionorambuenamiranda/PROYECTOS/1. PROYECTOS PRIORITARIOS/"
    "1. PROYECTO LUNA/2. Cajita de Luna"
)
DEFAULT_OPERATOR = Path(
    "/home/diegoignacionorambuenamiranda/Proyectos/1. PROYECTOS PRIORITARIOS/"
    "5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
)
DEFAULT_REPO = Path(__file__).resolve().parents[1] if "actions-runner" in str(Path(__file__)) else Path(
    "/home/diegoignacionorambuenamiranda/actions-runner/_work/luna-linux-bridge/luna-linux-bridge"
)
DEFAULT_OUTPUT = DEFAULT_OPERATOR / "CUSTOSZ_CONTINUITY_V1/state/jobs/cajita_luna_puac2_startup"
EXPECTED_DOMAINS = tuple(f"D{i:02d}" for i in range(1, 23))
BLOCKS = (
    ("B1", "FREEZE_AND_BASELINE"),
    ("B2", "FULL_INVENTORY_AND_REGISTRY_RECONCILIATION"),
    ("B3", "EXACT_BYTES_AND_RESOURCE_FEASIBILITY"),
    ("B4", "CUSTOSZ_V9_OPTIMIZATION_WITH_D01_D22"),
    ("B5", "FUNCTIONAL_VALIDATION_AND_EDGE"),
    ("B6", "CHECKPOINT_ROLLBACK_AND_NON_REGRESSION"),
    ("B7", "PUAC2_G23_G24"),
)
FROZEN_SCOPES = {
    "CEREBRO": "1. Cerebro",
    "TRANSCRIPCION": "3. Transcripción",
    "TRADUCCION_GENERAL": "4. Traductor Inteligente/Traducción general",
    "INTELIGENCIA_DOCUMENTAL": "5. Inteligencia documental",
    "ANALISIS_AVANZADO": "6. Sistema Inteligente/Análisis Avanzado",
}
CAP_BYTES = 470_000_000
EDGE_REL = (
    "2. Orquestación/Orquestador/EdgeBackup_20260907_170357_d18dac86743a/"
    "EdgeBackup_20260907_170357_d18dac86743a.7z"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(MIB), b""):
            digest.update(chunk)
    return digest.hexdigest()


def apply_controller_memory_limit() -> dict[str, int]:
    """Controller: 384 MiB soft, 1 GiB hard. Child gets at most 640 MiB."""
    old_soft, old_hard = resource.getrlimit(resource.RLIMIT_AS)
    hard_cap = GIB if old_hard == resource.RLIM_INFINITY else min(GIB, old_hard)
    soft_cap = min(CONTROLLER_AS_BYTES, hard_cap)
    resource.setrlimit(resource.RLIMIT_AS, (soft_cap, hard_cap))
    return {
        "controller_rlimit_as_soft_bytes": int(soft_cap),
        "controller_rlimit_as_hard_bytes": int(hard_cap),
        "requested_process_tree_budget_bytes": RAM_BUDGET_BYTES,
        "child_rlimit_as_bytes": min(CHILD_AS_BYTES, hard_cap),
    }


def available_ram_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def process_rss_bytes(pid: int) -> int:
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="ascii").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def descendants_rss_bytes(root_pid: int) -> int:
    """Sum RSS for one subprocess tree without scanning/controlling unrelated processes."""
    parents: dict[int, int] = {}
    rss: dict[int, int] = {}
    proc = Path("/proc")
    for item in proc.iterdir():
        if not item.name.isdigit():
            continue
        try:
            stat_fields = (item / "stat").read_text(encoding="ascii").split()
            pid = int(stat_fields[0])
            ppid = int(stat_fields[3])
            parents[pid] = ppid
            rss[pid] = process_rss_bytes(pid)
        except (OSError, ValueError, IndexError):
            continue
    selected = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, ppid in parents.items():
            if ppid in selected and pid not in selected:
                selected.add(pid)
                changed = True
    return sum(rss.get(pid, 0) for pid in selected)


def append_event(ledger_path: Path, event: dict[str, Any]) -> dict[str, Any]:
    previous_hash = "GENESIS"
    if ledger_path.is_file():
        try:
            last = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[-1])
            previous_hash = str(last["event_sha256"])
        except (OSError, ValueError, KeyError, IndexError):
            raise RuntimeError("EVENT_LEDGER_CHAIN_INVALID_FAIL_CLOSED")
    body = dict(event)
    body["previous_event_sha256"] = previous_hash
    event_hash = hashlib.sha256(canonical_json(body)).hexdigest()
    row = dict(body)
    row["event_sha256"] = event_hash
    with ledger_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return row


def validate_event_ledger(path: Path) -> bool:
    previous = "GENESIS"
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        claimed = row.pop("event_sha256")
        if row.get("previous_event_sha256") != previous:
            return False
        observed = hashlib.sha256(canonical_json(row)).hexdigest()
        if observed != claimed:
            return False
        previous = claimed
    return True


def _child_limit() -> None:
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = min(CHILD_AS_BYTES, GIB if hard == resource.RLIM_INFINITY else hard)
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))


def run_bounded_command(
    argv: list[str], output_dir: Path, label: str, timeout: int = CHILD_TIMEOUT_SECONDS
) -> dict[str, Any]:
    """Run a single read-only child with bounded address space and RSS telemetry."""
    start = time.monotonic()
    started_utc = utc_now()
    stdout_path = output_dir / f"{label}.stdout.log"
    stderr_path = output_dir / f"{label}.stderr.log"
    max_tree_rss = 0
    timed_out = False
    rss_budget_exceeded = False
    proc: subprocess.Popen[bytes] | None = None
    with stdout_path.open("wb") as stdout_stream, stderr_path.open("wb") as stderr_stream:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=stdout_stream,
            stderr=stderr_stream,
            start_new_session=True,
            preexec_fn=_child_limit,
            close_fds=True,
        )
        deadline = start + timeout
        while proc.poll() is None:
            observed = process_rss_bytes(os.getpid()) + descendants_rss_bytes(proc.pid)
            max_tree_rss = max(max_tree_rss, observed)
            if observed > RAM_BUDGET_BYTES:
                rss_budget_exceeded = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                break
            if time.monotonic() >= deadline:
                timed_out = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                break
            time.sleep(POLL_SECONDS)
        returncode = proc.wait()
    elapsed = round(time.monotonic() - start, 3)
    def read_tail(path: Path) -> str:
        try:
            with path.open("rb") as stream:
                stream.seek(0, os.SEEK_END)
                size = stream.tell()
                stream.seek(max(0, size - MAX_LOG_BYTES))
                return stream.read(MAX_LOG_BYTES).decode("utf-8", "replace")
        except OSError:
            return ""
    stdout = read_tail(stdout_path)
    stderr = read_tail(stderr_path)
    return {
        "argv": argv,
        "started_at_utc": started_utc,
        "finished_at_utc": utc_now(),
        "elapsed_seconds": elapsed,
        "returncode": returncode,
        "timed_out": timed_out,
        "process_tree_rss_peak_observed_bytes": max_tree_rss,
        "rss_budget_exceeded": rss_budget_exceeded,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "stdout_tail": stdout[-8000:],
        "stderr_tail": stderr[-4000:],
        "status": "PASS" if returncode == 0 and not timed_out and not rss_budget_exceeded else "FAIL",
    }


def load_json_text(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        value = json.loads(text[start : end + 1])
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def validate_domain_manifests(repo_root: Path) -> dict[str, Any]:
    domain_dir = repo_root / "implementation/super1200/domains"
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for domain in EXPECTED_DOMAINS:
        path = domain_dir / f"{domain}.json"
        row: dict[str, Any] = {"domain_id": domain, "path": str(path), "status": "MISSING"}
        if path.is_file() and not path.is_symlink():
            row["size_bytes"] = path.stat().st_size
            row["sha256"] = sha256_file(path)
            try:
                content = json.loads(path.read_text(encoding="utf-8"))
                row["json_parse"] = "PASS"
                row["top_level_keys"] = sorted(content.keys()) if isinstance(content, dict) else []
                row["status"] = "PRESENT_AND_PARSEABLE"
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                row["json_parse"] = "FAIL"
                row["error_type"] = type(exc).__name__
                errors.append(f"{domain}:JSON_INVALID")
        else:
            errors.append(f"{domain}:MANIFEST_MISSING_OR_UNSAFE")
        rows.append(row)
    return {
        "domain_count_expected": len(EXPECTED_DOMAINS),
        "domain_count_present_and_parseable": sum(x["status"] == "PRESENT_AND_PARSEABLE" for x in rows),
        "errors": errors,
        "domains": rows,
    }


def hash_frozen_scopes(cajita_root: Path) -> dict[str, Any]:
    """Hash only the frozen-scope file bytes; never expose file contents."""
    result: dict[str, Any] = {"scopes": {}, "errors": []}
    for name, rel in FROZEN_SCOPES.items():
        scope = cajita_root / rel
        row = {"relative_path": rel, "files": [], "file_count": 0, "total_bytes": 0, "status": "BLOCKED"}
        if not scope.is_dir() or scope.is_symlink():
            result["errors"].append(f"{name}:SCOPE_MISSING_OR_UNSAFE")
            result["scopes"][name] = row
            continue
        for base, dirs, files in os.walk(scope, topdown=True, followlinks=False):
            dirs.sort()
            files.sort()
            base_path = Path(base)
            for directory in list(dirs):
                candidate = base_path / directory
                if candidate.is_symlink():
                    result["errors"].append(f"{name}:SYMLINK_DIRECTORY:{candidate.relative_to(cajita_root).as_posix()}")
                    dirs.remove(directory)
            for filename in files:
                path = base_path / filename
                try:
                    info = path.lstat()
                    rel_path = path.relative_to(cajita_root).as_posix()
                    if path.is_symlink() or not path.is_file():
                        result["errors"].append(f"{name}:NONREGULAR_OR_SYMLINK:{rel_path}")
                        continue
                    digest = sha256_file(path)
                    row["files"].append({"path": rel_path, "size_bytes": info.st_size, "sha256": digest})
                    row["file_count"] += 1
                    row["total_bytes"] += info.st_size
                except OSError as exc:
                    result["errors"].append(f"{name}:READ_ERROR:{path.relative_to(cajita_root).as_posix()}:{type(exc).__name__}")
        row["files"].sort(key=lambda item: item["path"])
        row["status"] = "PASS" if row["file_count"] > 0 else "BLOCKED_EMPTY_OR_UNREADABLE"
        if row["status"] != "PASS":
            result["errors"].append(f"{name}:NO_HASHED_FILES")
        row["manifest_sha256"] = hashlib.sha256(canonical_json(row["files"])).hexdigest()
        result["scopes"][name] = row
    result["status"] = "PASS" if not result["errors"] else "BLOCKED"
    return result


def validate_block_order(block_results: list[dict[str, Any]]) -> bool:
    ids = [row.get("block_id") for row in block_results]
    if ids != [block_id for block_id, _ in BLOCKS[: len(ids)]]:
        return False
    held = False
    for row in block_results:
        status = row.get("status")
        if held and status != "NOT_STARTED_PREDECESSOR_HOLD":
            return False
        if status in {"HOLD", "FAIL"}:
            held = True
    return True


def transformations_allowed(custos_status: dict[str, Any], plan_status: str, preflight_status: str) -> bool:
    return (
        custos_status.get("active_authorized") is True
        and custos_status.get("certification") == "GRANTED"
        and plan_status == "PASS"
        and preflight_status == "READY_FOR_CONTROLLED_OPTIMIZATION"
    )


def _load_preflight_module(repo_root: Path):
    path = repo_root / "scripts/cajita_luna_governed_preflight.py"
    if not path.is_file():
        raise FileNotFoundError("GOVERNED_PREFLIGHT_SCRIPT_MISSING_ON_MAIN")
    spec = importlib.util.spec_from_file_location("cajita_luna_governed_preflight_local", path)
    if spec is None or spec.loader is None:
        raise ImportError("GOVERNED_PREFLIGHT_MODULE_COULD_NOT_LOAD")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _block(block_id: str, name: str, status: str, started: str, detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "block_id": block_id,
        "name": name,
        "status": status,
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "details": detail,
    }


def run_startup(args: argparse.Namespace) -> dict[str, Any]:
    started_wall = utc_now()
    started_mono = time.monotonic()
    limits = apply_controller_memory_limit()
    output_root = args.output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = output_root / run_id
    run_dir.mkdir(mode=0o700)
    ledger = run_dir / "events.jsonl"
    report_path = run_dir / "startup_report.json"
    event = lambda event_type, payload: append_event(ledger, {
        "timestamp_utc": utc_now(), "event_type": event_type, "payload": payload
    })
    event("CONTROLLER_START", {
        "run_id": run_id, "repo_root": str(args.repo_root), "repo_commit": args.repo_commit,
        "cajita_root": str(args.cajita_root), "ram_budget_bytes": RAM_BUDGET_BYTES,
        "memory_limits": limits, "payload_transformations_performed": False,
    })

    if not args.repo_root.is_dir() or not args.cajita_root.is_dir():
        raise FileNotFoundError("REPOSITORY_OR_CAJITA_ROOT_MISSING")
    repo_root = args.repo_root.resolve(strict=True)
    cajita_root = args.cajita_root.resolve(strict=True)
    preflight_module = _load_preflight_module(repo_root)
    v9 = args.custosz_package
    v9_commands: list[dict[str, Any]] = []
    version_command = run_bounded_command([sys.executable, str(v9), "--version"], run_dir, "custosz_v9_version")
    v9_commands.append(version_command)
    status_command = run_bounded_command([sys.executable, str(v9), "crfu", "status"], run_dir, "custosz_v9_crfu_status")
    v9_commands.append(status_command)
    v9_status = load_json_text(status_command["stdout_tail"])
    selftest_command = run_bounded_command([sys.executable, str(v9), "crfu", "selftest"], run_dir, "custosz_v9_crfu_selftest")
    v9_commands.append(selftest_command)
    v9_selftest = load_json_text(selftest_command["stdout_tail"])
    event("CUSTOSZ_V9_PREFLIGHT", {
        "package_path": str(v9), "package_sha256": sha256_file(v9) if v9.is_file() else None,
        "version_command_status": version_command["status"],
        "crfu_status": v9_status, "selftest_status": v9_selftest.get("status"),
        "authorization_granted": v9_selftest.get("authorization_granted"),
    })

    domain_manifests = validate_domain_manifests(repo_root)
    event("D01_D22_MANIFESTS_CHECKED", {
        "present_and_parseable": domain_manifests["domain_count_present_and_parseable"],
        "expected": domain_manifests["domain_count_expected"],
        "errors": domain_manifests["errors"],
    })

    blocks: list[dict[str, Any]] = []
    block1_start = utc_now()
    event("B1_START", {"action": "READ_ONLY_FREEZE_AND_BASELINE"})
    inventory = preflight_module.scan_tree(cajita_root)
    frozen = hash_frozen_scopes(cajita_root)
    edge_path = cajita_root / EDGE_REL
    edge_detail: dict[str, Any] = {"relative_path": EDGE_REL, "status": "MISSING"}
    if edge_path.is_file() and not edge_path.is_symlink():
        edge_detail = {
            "relative_path": EDGE_REL,
            "size_bytes": edge_path.stat().st_size,
            "sha256": sha256_file(edge_path),
            "status": "HASHED_READ_ONLY",
        }
    block1_status = "PASS" if (
        not inventory["scan_errors"] and not inventory["symlinks"]
        and not inventory["hardlink_groups"] and not inventory["non_regular"]
        and frozen["status"] == "PASS" and edge_detail.get("sha256")
    ) else "HOLD"
    blocks.append(_block("B1", BLOCKS[0][1], block1_status, block1_start, {
        "measurement_policy": "READ_ONLY; stream hashes; no payload mutation",
        "tree_total_bytes": inventory["total_bytes"],
        "regular_file_count": inventory["regular_file_count"],
        "entry_count": inventory["entry_count"],
        "symlinks": inventory["symlinks"],
        "hardlink_groups": inventory["hardlink_groups"],
        "non_regular": inventory["non_regular"],
        "scan_errors": inventory["scan_errors"],
        "frozen_outputs": frozen,
        "edge_archive": edge_detail,
    }))
    event("B1_FINISH", {
        "status": block1_status, "tree_total_bytes": inventory["total_bytes"],
        "frozen_manifest_sha256": hashlib.sha256(canonical_json(frozen)).hexdigest(),
        "edge_sha256": edge_detail.get("sha256"),
    })

    registry: dict[str, Any] = {"status": "NOT_RUN_PREDECESSOR_HOLD"}
    reconciliation_errors: list[str] = ["B1_PREDECESSOR_NOT_PASSED"]
    frozen_manifest_errors: list[str] = ["B1_PREDECESSOR_NOT_PASSED"]
    plan: dict[str, Any] = {"status": "NOT_RUN_PREDECESSOR_HOLD", "errors": ["PREDECESSOR_NOT_PASSED"]}
    plan_status = "NOT_RUN_PREDECESSOR_HOLD"
    free_bytes: int | None = None
    available_ram: int | None = None
    edge_bytes = edge_detail.get("size_bytes")
    tree_bytes = inventory["total_bytes"]
    size_overage = max(0, tree_bytes - CAP_BYTES)
    edge_overage = max(0, int(edge_bytes or 0) - CAP_BYTES)
    block2_status = "NOT_STARTED_PREDECESSOR_HOLD"
    block3_status = "NOT_STARTED_PREDECESSOR_HOLD"

    if block1_status != "PASS":
        event("B2_NOT_STARTED", {"reason": "B1_NOT_PASS"})
        blocks.append(_block("B2", BLOCKS[1][1], block2_status, utc_now(), {
            "reason": "B1 failed its baseline gate; strict order forbids entering B2.",
            "registry_modified": False,
        }))
        blocks.append(_block("B3", BLOCKS[2][1], block3_status, utc_now(), {
            "reason": "B2 was not started because B1 did not pass.",
            "write_authorized": False,
        }))
    else:
        block2_start = utc_now()
        event("B2_START", {"action": "READ_ONLY_INVENTORY_AND_REGISTRY_RECONCILIATION"})
        registry = preflight_module.registry_comparison(cajita_root)
        reconciliation_errors = preflight_module.validate_reconciliation(cajita_root, registry)
        frozen_manifest_errors = preflight_module.validate_frozen_manifest(cajita_root)
        d01_d22_status = "PASS" if not domain_manifests["errors"] else "HOLD"
        block2_status = "PASS" if (
            not reconciliation_errors and not frozen_manifest_errors
            and d01_d22_status == "PASS" and not inventory["scan_errors"]
        ) else "HOLD"
        blocks.append(_block("B2", BLOCKS[1][1], block2_status, block2_start, {
            "legacy_registry": registry,
            "reconciliation_errors": reconciliation_errors,
            "frozen_manifest_errors": frozen_manifest_errors,
            "domain_manifests": domain_manifests,
            "source_artifacts_modified": False,
            "registry_modified": False,
            "missing_or_mismatched_paths_repaired_by_guess": False,
        }))
        event("B2_FINISH", {
            "status": block2_status, "reconciliation_errors": reconciliation_errors,
            "frozen_manifest_errors": frozen_manifest_errors,
            "domains_validated": domain_manifests["domain_count_present_and_parseable"],
        })

        if block2_status != "PASS":
            event("B3_NOT_STARTED", {"reason": "B2_NOT_PASS"})
            blocks.append(_block("B3", BLOCKS[2][1], block3_status, utc_now(), {
                "reason": "B2 reconciliation gate has not passed; strict order forbids entering B3.",
                "current_tree_bytes": tree_bytes,
                "hard_cap_bytes": CAP_BYTES,
                "current_overage_bytes": size_overage,
                "edge_archive_bytes": edge_bytes,
                "edge_alone_overage_bytes": edge_overage,
                "write_authorized": False,
            }))
        else:
            block3_start = utc_now()
            event("B3_START", {"action": "EXACT_BYTES_AND_RESOURCE_FEASIBILITY"})
            disk = os.statvfs(cajita_root)
            free_bytes = disk.f_bavail * disk.f_frsize
            available_ram = available_ram_bytes()
            plan = preflight_module.validate_plan(cajita_root, tree_bytes, free_bytes, available_ram)
            plan_status = str(plan.get("status", "HOLD"))
            blockers = []
            if tree_bytes > CAP_BYTES:
                blockers.append("CURRENT_TREE_OVER_CAP")
            if edge_overage > 0:
                blockers.append("CURRENT_EDGE_ARCHIVE_ALONE_EXCEEDS_CAP")
            if plan_status != "PASS":
                blockers.append("QUANTITATIVE_PLAN_OR_DEPENDENCY_BOUNDS_NOT_PASS")
            if available_ram is None or available_ram < RAM_BUDGET_BYTES:
                blockers.append("INSUFFICIENT_OR_UNKNOWN_AVAILABLE_RAM_FOR_1GIB_BUDGET")
            if not transformations_allowed(v9_status, plan_status, "READY_FOR_CONTROLLED_OPTIMIZATION"):
                blockers.append("CUSTOSZ_V9_ACTIVE_AUTHORIZATION_NOT_GRANTED")
            block3_status = "PASS" if not blockers else "HOLD"
            blocks.append(_block("B3", BLOCKS[2][1], block3_status, block3_start, {
                "current_tree_bytes": tree_bytes,
                "hard_cap_bytes": CAP_BYTES,
                "current_overage_bytes": size_overage,
                "edge_archive_bytes": edge_bytes,
                "edge_alone_overage_bytes": edge_overage,
                "partition_free_bytes": free_bytes,
                "host_mem_available_bytes": available_ram,
                "controller_ram_budget_bytes": RAM_BUDGET_BYTES,
                "resource_limits": limits,
                "optimization_plan_preflight": plan,
                "output_upper_bounds_provided_and_verified": False,
                "final_exact_upper_bound_bytes": None,
                "blockers": blockers,
                "write_authorized": False,
            }))
            event("B3_FINISH", {
                "status": block3_status, "current_tree_bytes": tree_bytes,
                "cap_bytes": CAP_BYTES, "current_overage_bytes": size_overage,
                "edge_archive_bytes": edge_bytes, "blockers": blockers,
            })

    predecessor_hold = any(row["status"] in {"HOLD", "FAIL"} for row in blocks)
    later_block_ids = [item[0] for item in BLOCKS[3:]]
    for block_id, name in BLOCKS[3:]:
        if predecessor_hold or not transformations_allowed(v9_status, plan_status, "READY_FOR_CONTROLLED_OPTIMIZATION"):
            blocks.append(_block(
                block_id, name, "NOT_STARTED_PREDECESSOR_HOLD", utc_now(),
                {"reason": "Earlier block or authorization gate has not passed; no work skipped or dispatched."},
            ))
        else:
            # This controller intentionally does not implement payload operations.
            blocks.append(_block(
                block_id, name, "NOT_STARTED_EXECUTOR_REQUIRED", utc_now(),
                {"reason": "Requires the separately authorized CUSTOSZ V9 mission worker; controller never transforms payloads."},
            ))
    ordered = validate_block_order(blocks)
    if not ordered:
        raise RuntimeError("CANONICAL_SEVEN_BLOCK_ORDER_INVALID_FAIL_CLOSED")

    telemetry = {
        "captured_at_utc": utc_now(),
        "controller_rss_bytes": process_rss_bytes(os.getpid()),
        "host_mem_available_bytes": available_ram_bytes(),
        "ram_budget_bytes": RAM_BUDGET_BYTES,
        "controller_memory_limits": limits,
        "payload_transformations_performed": False,
        "edge_removed_or_moved": False,
        "frozen_scopes_modified": False,
        "github_repo_commit": args.repo_commit,
    }
    mission_started = (
        blocks[0]["status"] == "PASS"
        and blocks[1]["status"] == "PASS"
        and blocks[2]["status"] == "PASS"
        and transformations_allowed(v9_status, plan_status, "READY_FOR_CONTROLLED_OPTIMIZATION")
    )
    report = {
        "schema": "CAJITA_PUAC2_SEQUENTIAL_STARTUP/1.0",
        "run_id": run_id,
        "controller_startup": "SUCCESS_TELEMETRY_CONFIRMED",
        "mission_startup": "AUTHORIZED_WORKER_NOT_STARTED" if not mission_started else "READY_FOR_EXECUTOR_DISPATCH",
        "mission_status": "HOLD" if not mission_started else "READY",
        "started_at_utc": started_wall,
        "finished_at_utc": utc_now(),
        "elapsed_seconds": round(time.monotonic() - started_mono, 3),
        "repo": {"root": str(repo_root), "commit": args.repo_commit},
        "cajita_root": str(cajita_root),
        "custosz_v9": {
            "package": str(v9),
            "package_sha256": sha256_file(v9) if v9.is_file() else None,
            "status": v9_status,
            "selftest": {
                "status": v9_selftest.get("status"),
                "check_count": v9_selftest.get("check_count"),
                "failed_checks": v9_selftest.get("failed_checks"),
                "authorization_granted": v9_selftest.get("authorization_granted"),
                "external_host_operations": v9_selftest.get("external_host_operations"),
            },
            "commands": v9_commands,
            "transform_worker_started": False,
        },
        "domain_manifests": {
            "count_expected": domain_manifests["domain_count_expected"],
            "count_validated": domain_manifests["domain_count_present_and_parseable"],
            "errors": domain_manifests["errors"],
            "manifest_digests": [
                {"domain_id": item["domain_id"], "sha256": item.get("sha256"), "status": item["status"]}
                for item in domain_manifests["domains"]
            ],
        },
        "blocks_in_canonical_order": ordered,
        "blocks": blocks,
        "telemetry": telemetry,
        "events_ledger": str(ledger),
        "events_ledger_sha256": sha256_file(ledger),
        "events_ledger_chain_valid": validate_event_ledger(ledger),
        "report_path": str(report_path),
        "payload_write_operations": 0,
        "block4_dispatch_performed": False,
        "g23_performed": False,
        "g24_issued": False,
        "certification_status": "NOT_GRANTED",
    }
    event("STARTUP_DECISION", {
        "controller_startup": report["controller_startup"],
        "mission_startup": report["mission_startup"],
        "mission_status": report["mission_status"],
        "block_statuses": [{"block_id": b["block_id"], "status": b["status"]} for b in blocks],
        "certification_status": "NOT_GRANTED",
    })
    report["events_ledger_sha256"] = sha256_file(ledger)
    report["events_ledger_chain_valid"] = validate_event_ledger(ledger)
    report["finished_at_utc"] = utc_now()
    temp = report_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    with temp.open("rb") as stream:
        os.fsync(stream.fileno())
    os.replace(temp, report_path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cajita-root", type=Path, default=DEFAULT_CAJITA)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--repo-commit", default="UNKNOWN")
    parser.add_argument("--custosz-package", type=Path, default=DEFAULT_OPERATOR / "CUSTOSZV9.pyz")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = run_startup(args)
        print(json.dumps({
            "schema": report["schema"],
            "run_id": report["run_id"],
            "controller_startup": report["controller_startup"],
            "mission_startup": report["mission_startup"],
            "mission_status": report["mission_status"],
            "elapsed_seconds": report["elapsed_seconds"],
            "report_path": report["report_path"],
            "events_ledger": report["events_ledger"],
            "events_ledger_chain_valid": report["events_ledger_chain_valid"],
            "blocks": [{"block_id": x["block_id"], "status": x["status"]} for x in report["blocks"]],
            "custosz_v9_authorized": report["custosz_v9"]["status"].get("active_authorized") is True,
            "certification_status": report["certification_status"],
        }, sort_keys=True, indent=2, ensure_ascii=False))
        return 0 if report["controller_startup"] == "SUCCESS_TELEMETRY_CONFIRMED" and report["events_ledger_chain_valid"] else 3
    except Exception as exc:
        print(json.dumps({
            "schema": "CAJITA_PUAC2_SEQUENTIAL_STARTUP_ERROR/1.0",
            "status": "HOLD",
            "error_type": type(exc).__name__,
            "reason": str(exc),
            "captured_at_utc": utc_now(),
            "certification_status": "NOT_GRANTED",
        }, sort_keys=True, indent=2, ensure_ascii=False))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
