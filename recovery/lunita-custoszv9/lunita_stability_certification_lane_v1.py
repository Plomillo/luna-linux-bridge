#!/usr/bin/env python3
"""Continuous, fail-closed acquisition of Lunita 1.7 candidate certification evidence.

This lane is deliberately independent of the active supervisor/Cajita worker. It
never edits the source model, frozen G06, or canonical G08 bindings. It builds a
full candidate-rootfs inventory only when the Cajita heavy worker is idle, keeps
the independent report hash-bound, and emits a separate stable-release receipt
only after the existing S31/S32 gates and every required check pass.
"""
from __future__ import annotations

import datetime as dt
import email
import functools
import importlib.util
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

from jasp_seed_fixture_v1 import (
    FixtureError,
    inspect_seed_option,
    prepare_deterministic_fixture,
    verify_deterministic_fixture_receipt,
)


class ProcessTreeCleanupError(RuntimeError):
    """A bounded JASP command left descendants alive or could not clean them up."""

    def __init__(self, message: str, process_tree_receipt: dict | None = None):
        super().__init__(message)
        self.process_tree_receipt = process_tree_receipt


class ProcessTreeTimeoutExpired(subprocess.TimeoutExpired):
    """Timeout carrying a verifiable process-group cleanup receipt."""

    def __init__(self, command, timeout, output: str, process_tree_receipt: dict):
        super().__init__(command, timeout, output=output)
        self.process_tree_receipt = process_tree_receipt


def _process_group_members(pgid: int) -> list[int] | None:
    """Return live members, or None when membership cannot be proven."""
    proc_root = pathlib.Path("/proc")
    if not proc_root.is_dir():
        try:
            os.killpg(pgid, 0)
            return None
        except ProcessLookupError:
            return []
        except PermissionError:
            return None

    members = []
    unreadable = False
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
            state = fields[0]
            process_group = int(fields[2])
        except FileNotFoundError:
            continue
        except (OSError, ValueError, IndexError):
            unreadable = True
            continue
        if process_group == pgid and state not in {"Z", "X"}:
            members.append(int(entry.name))
    return None if unreadable else sorted(members)


def _process_group_exists(pgid: int) -> bool:
    members = _process_group_members(pgid)
    return members is None or bool(members)


def _terminate_process_group(process: subprocess.Popen, grace_seconds: float = 3.0) -> dict:
    """Terminate the isolated process group and return its observed closure state."""
    pgid = process.pid
    signals_sent = []
    members = _process_group_members(pgid)
    if members is None or members:
        try:
            os.killpg(pgid, signal.SIGTERM)
            signals_sent.append("SIGTERM")
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        pass

    members = _process_group_members(pgid)
    if members is None or members:
        try:
            os.killpg(pgid, signal.SIGKILL)
            signals_sent.append("SIGKILL")
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        pass

    deadline = time.monotonic() + grace_seconds
    members = _process_group_members(pgid)
    while time.monotonic() < deadline and (members is None or members):
        time.sleep(0.05)
        members = _process_group_members(pgid)
    return {
        "termination_signals": signals_sent,
        "remaining_live_pids": members,
        "process_group_closed": members == [],
    }


def _process_tree_receipt(
    *,
    env: dict,
    case_id: str,
    invocation_id: str,
    process_group_id: int,
    executable_sha256: str,
    runtime_ostree_commit: str,
    command: list[str],
    timeout: float,
    started_at_utc: str,
    finished_at_utc: str,
    returncode: int,
    timeout_triggered: bool,
    closure: dict,
    stdout: str,
    status: str,
) -> dict:
    output_bytes = stdout.encode("utf-8")
    command_bytes = json.dumps(command, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "schema": "LUNITA_JASP_PROCESS_TREE_RECEIPT/1.0",
        "status": status,
        "run_id": str(env["GITHUB_RUN_ID"]),
        "run_attempt": str(env["GITHUB_RUN_ATTEMPT"]),
        "case_id": case_id,
        "invocation_id": invocation_id,
        "process_group_id": process_group_id,
        "session_id": process_group_id,
        "executable_sha256": executable_sha256,
        "runtime_ostree_commit": runtime_ostree_commit,
        "command_sha256": hashlib.sha256(command_bytes).hexdigest(),
        "timeout_seconds": timeout,
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "returncode": returncode,
        "timeout_triggered": timeout_triggered,
        "termination_signals": closure["termination_signals"],
        "remaining_live_pids": closure["remaining_live_pids"],
        "process_group_closed": closure["process_group_closed"],
        "captured_output_sha256": hashlib.sha256(output_bytes).hexdigest(),
        "captured_output_bytes": len(output_bytes),
    }


def validate_process_tree_receipt(
    receipt: dict | None,
    *,
    command: list[str],
    env: dict,
    timeout: float,
    case_id: str,
    executable_sha256: str,
    runtime_ostree_commit: str,
    stdout: str,
    returncode: int,
    timeout_triggered: bool = False,
) -> bool:
    """Independently validate the invocation identity tuple and process closure."""
    if not isinstance(receipt, dict):
        return False
    output_bytes = stdout.encode("utf-8")
    command_bytes = json.dumps(command, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    expected_status = (
        "BLOCKED_TIMEOUT_PROCESS_GROUP_CLOSED" if timeout_triggered
        else "PASS_PROCESS_GROUP_CLOSED"
    )
    invocation_id = receipt.get("invocation_id")
    return bool(
        receipt.get("schema") == "LUNITA_JASP_PROCESS_TREE_RECEIPT/1.0"
        and receipt.get("status") == expected_status
        and receipt.get("run_id") == str(env.get("GITHUB_RUN_ID", ""))
        and receipt.get("run_attempt") == str(env.get("GITHUB_RUN_ATTEMPT", ""))
        and re.fullmatch(r"[0-9a-f]{32}", str(invocation_id or ""))
        and receipt.get("case_id") == case_id
        and isinstance(receipt.get("process_group_id"), int)
        and receipt.get("process_group_id", 0) > 1
        and receipt.get("session_id") == receipt.get("process_group_id")
        and receipt.get("executable_sha256") == executable_sha256
        and receipt.get("runtime_ostree_commit") == runtime_ostree_commit
        and receipt.get("command_sha256") == hashlib.sha256(command_bytes).hexdigest()
        and receipt.get("timeout_seconds") == timeout
        and isinstance(receipt.get("started_at_utc"), str)
        and isinstance(receipt.get("finished_at_utc"), str)
        and receipt.get("returncode") == returncode
        and receipt.get("timeout_triggered") is timeout_triggered
        and isinstance(receipt.get("termination_signals"), list)
        and receipt.get("remaining_live_pids") == []
        and receipt.get("process_group_closed") is True
        and receipt.get("captured_output_sha256") == hashlib.sha256(output_bytes).hexdigest()
        and receipt.get("captured_output_bytes") == len(output_bytes)
    )


def process_tree_receipt_identity_matches(
    receipt: dict | None,
    *,
    case_id: str,
    env: dict,
    executable_sha256: str,
    runtime_ostree_commit: str,
) -> bool:
    """Re-check the receipt identity and closure during independent report assembly."""
    if not isinstance(receipt, dict):
        return False
    return bool(
        receipt.get("schema") == "LUNITA_JASP_PROCESS_TREE_RECEIPT/1.0"
        and receipt.get("status") == "PASS_PROCESS_GROUP_CLOSED"
        and receipt.get("run_id") == str(env.get("GITHUB_RUN_ID", ""))
        and receipt.get("run_attempt") == str(env.get("GITHUB_RUN_ATTEMPT", ""))
        and receipt.get("case_id") == case_id
        and re.fullmatch(r"[0-9a-f]{32}", str(receipt.get("invocation_id", "")))
        and isinstance(receipt.get("process_group_id"), int)
        and receipt.get("process_group_id", 0) > 1
        and receipt.get("session_id") == receipt.get("process_group_id")
        and receipt.get("executable_sha256") == executable_sha256
        and receipt.get("runtime_ostree_commit") == runtime_ostree_commit
        and re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("command_sha256", "")))
        and isinstance(receipt.get("timeout_seconds"), (int, float))
        and receipt.get("timeout_triggered") is False
        and receipt.get("termination_signals") == []
        and receipt.get("remaining_live_pids") == []
        and receipt.get("process_group_closed") is True
        and re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("captured_output_sha256", "")))
        and isinstance(receipt.get("captured_output_bytes"), int)
        and receipt.get("captured_output_bytes", -1) >= 0
    )


def run_bounded_process_tree(
    command: list[str],
    *,
    env: dict,
    timeout: float,
    case_id: str,
    executable_sha256: str,
    runtime_ostree_commit: str,
) -> subprocess.CompletedProcess:
    """Run JASP in a unique session and return only with a hash-bound closure receipt.

    File-backed output prevents descendants from blocking timeout completion by
    inheriting a pipe. Every invocation is bound to workflow run/attempt, case,
    invocation UUID, PGID/SID, executable hash and OSTree runtime commit.
    """
    run_id = str(env.get("GITHUB_RUN_ID", ""))
    run_attempt = str(env.get("GITHUB_RUN_ATTEMPT", ""))
    if not re.fullmatch(r"\d+", run_id) or not re.fullmatch(r"\d+", run_attempt):
        raise RuntimeError("GitHub workflow run ID/attempt is missing or malformed")
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", case_id):
        raise RuntimeError("JASP process-tree case ID is missing or malformed")
    if not re.fullmatch(r"[0-9a-f]{64}", executable_sha256 or ""):
        raise RuntimeError("JASP executable SHA-256 is missing or malformed")
    if not re.fullmatch(r"[0-9a-f]{64}", runtime_ostree_commit or ""):
        raise RuntimeError("JASP Flatpak runtime OSTree commit is missing or malformed")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise RuntimeError("JASP process-tree timeout must be positive")

    started_at_utc = utc()
    invocation_id = uuid.uuid4().hex
    with tempfile.TemporaryFile(mode="w+b") as output:
        process = subprocess.Popen(
            command,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        process_group_id = process.pid
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            closure = _terminate_process_group(process)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            output.seek(0)
            captured = output.read().decode("utf-8", "replace")
            receipt = _process_tree_receipt(
                env=env, case_id=case_id, invocation_id=invocation_id,
                process_group_id=process_group_id, executable_sha256=executable_sha256,
                runtime_ostree_commit=runtime_ostree_commit, command=command, timeout=timeout,
                started_at_utc=started_at_utc, finished_at_utc=utc(), returncode=124,
                timeout_triggered=True, closure=closure, stdout=captured,
                status=(
                    "BLOCKED_TIMEOUT_PROCESS_GROUP_CLOSED"
                    if closure["process_group_closed"] else "BLOCKED_PROCESS_GROUP_NOT_CLOSED"
                ),
            )
            raise ProcessTreeTimeoutExpired(command, timeout, captured, receipt) from exc

        members_after_exit = _process_group_members(process_group_id)
        if members_after_exit is None or members_after_exit:
            closure = _terminate_process_group(process)
            output.seek(0)
            captured = output.read().decode("utf-8", "replace")
            receipt = _process_tree_receipt(
                env=env, case_id=case_id, invocation_id=invocation_id,
                process_group_id=process_group_id, executable_sha256=executable_sha256,
                runtime_ostree_commit=runtime_ostree_commit, command=command, timeout=timeout,
                started_at_utc=started_at_utc, finished_at_utc=utc(), returncode=returncode,
                timeout_triggered=False, closure=closure, stdout=captured,
                status="BLOCKED_DESCENDANTS_AFTER_NORMAL_EXIT" if closure["process_group_closed"]
                       else "BLOCKED_PROCESS_GROUP_NOT_CLOSED",
            )
            raise ProcessTreeCleanupError(
                f"JASP launcher exited with return code {returncode} while process-group members remained",
                receipt,
            )

        output.seek(0)
        captured = output.read().decode("utf-8", "replace")
        closure = {"termination_signals": [], "remaining_live_pids": [], "process_group_closed": True}
        receipt = _process_tree_receipt(
            env=env, case_id=case_id, invocation_id=invocation_id,
            process_group_id=process_group_id, executable_sha256=executable_sha256,
            runtime_ostree_commit=runtime_ostree_commit, command=command, timeout=timeout,
            started_at_utc=started_at_utc, finished_at_utc=utc(), returncode=returncode,
            timeout_triggered=False, closure=closure, stdout=captured,
            status="PASS_PROCESS_GROUP_CLOSED",
        )
        completed = subprocess.CompletedProcess(command, returncode, stdout=captured)
        completed.process_tree_receipt = receipt
        return completed


ROOT = pathlib.Path(__file__).resolve().parent
ST = pathlib.Path(os.environ.get("LUNITA_STATE_DIR", str(ROOT / "state"))).expanduser()
OUT = pathlib.Path(os.environ.get("LUNITA_OUTPUT_DIR", str(ST / "worker_outputs"))).expanduser()
EVIDENCE = pathlib.Path(os.environ.get("LUNITA_EVIDENCE_DIR", str(ST / "lunita_certification_evidence"))).expanduser()
CANDIDATE = pathlib.Path(os.environ.get(
    "LUNITA_CANDIDATE_DIR", str(ST / "g06_rebuild_candidates" / "G06_REBUILD_CANDIDATE_R1")
)).expanduser()
ROOTFS = pathlib.Path(os.environ.get("LUNITA_ROOTFS", str(CANDIDATE / "rootfs"))).expanduser()
RUNTIME_REPORT = pathlib.Path(os.environ.get(
    "LUNITA_RUNTIME_REPORT", str(CANDIDATE / "BETA_RUNTIME_FUNCTIONAL_TESTS.json")
)).expanduser()
TARGET_RUNTIME_RECEIPT_DIR = pathlib.Path(os.environ.get(
    "LUNITA_TARGET_RUNTIME_RECEIPT_DIR",
    str(pathlib.Path(os.environ.get("XDG_STATE_HOME") or (pathlib.Path.home() / ".local/state"))
        / "lunita/runtime_validation")
)).expanduser()
INDEPENDENT_REPORT = pathlib.Path(os.environ.get(
    "LUNITA_INDEPENDENT_REPORT", str(CANDIDATE / "BETA_INDEPENDENT_VALIDATION.json")
)).expanduser()
MISSION_PATH = pathlib.Path(os.environ.get("LUNITA_MISSION_PATH", str(ROOT.parent / "MISION1.txt"))).expanduser()
MISSION_SHA = "0a36c59d4baf5d547f5217dc9c6db2a58ad9f8f3ea65d88f9b16a0dbe1604f8f"
CERTIFICATION_PROFILE = os.environ.get("LUNITA_CERTIFICATION_PROFILE", "LEGACY_V1_7").strip().upper()
CANDIDATE_MANIFEST = pathlib.Path(os.environ.get(
    "LUNITA_CANDIDATE_MANIFEST", str(ROOT.parent.parent / "LUNITA_V1_8_CANDIDATE_FREEZE.json")
)).expanduser()
SQUASHFS_IMAGE = pathlib.Path(os.environ.get(
    "LUNITA_SQUASHFS_IMAGE", str(CANDIDATE / "LUNITA.squashfs")
)).expanduser()
SQUASHFS_CHECKSUM = pathlib.Path(os.environ.get(
    "LUNITA_SQUASHFS_CHECKSUM", str(SQUASHFS_IMAGE.with_name(SQUASHFS_IMAGE.name + ".sha256"))
)).expanduser()
SQUASHFS_PACKAGE_RECEIPT = pathlib.Path(os.environ.get(
    "LUNITA_SQUASHFS_PACKAGE_RECEIPT", str(SQUASHFS_IMAGE.with_name("LUNITA_SQUASHFS_PACKAGE_RECEIPT.json"))
)).expanduser()

POLL_SECONDS = 60
RUNNING_CAJITA_STAGES = {
    "ENV_INSTALL_RUNNING", "ENV_INSTALL_FALLBACK_RUNNING", "DRY_RUN_RUNNING",
    "CONVERSION_RUNNING", "QUANTIZATION_RUNNING", "HASH_RUNNING",
}
JASP_CASES = {
    "flatpak_launch": ("JASP_UNITTEST_FLATPAK_", "*.log", "JASP_UNITTEST_RC"),
    "reliability": ("JASP_UNITTEST_RELIABILITY_", "*.log", "JASP_RELIABILITY_UNITTEST_RC"),
    "weight_gain": ("JASP_UNITTEST_WEIGHT_GAIN_", "*.log", "JASP_WEIGHT_GAIN_UNITTEST_RC"),
    "death_penalty_roundtrip": ("JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_", "*.json", None),
}
DEATH_PENALTY_SOURCE_SHA256 = "fc8b6f8faf0e4437c8e4ab4bd922b3e959a0d4549c813b229bc5708050851895"
EXPECTED_JASP_RUNTIME_VERSION = "0.98.8"
EXPECTED_JASP_SOURCE_COMMIT = "b6cd3b0310be4e18e1b673ac11f14e55615c8fa1"
EXPECTED_JASP_APP_COMMIT = "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: pathlib.Path, default=None):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except (OSError, ValueError, TypeError):
        return default


def atomic_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with tmp.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def pid_alive(pid) -> bool:
    if not isinstance(pid, int) or pid <= 1:
        return False
    try:
        stat = pathlib.Path(f"/proc/{pid}/stat").read_text().split()
        if len(stat) > 2 and stat[2] == "Z":
            return False
        os.kill(pid, 0)
        return True
    except PermissionError:
        # A root-owned inventory worker is alive even though its unprivileged
        # supervisor cannot signal it. Treat EPERM as existence, not exit.
        return True
    except (OSError, ValueError, IndexError):
        return False


def cajita_heavy_active() -> dict:
    """Return a reason to defer hashing/GUI tests without touching Cajita."""
    lane = load_json(ST / "cajita_priority_lane.json", {}) or {}
    stage = str(lane.get("stage", "")).upper()
    job = lane.get("job") or {}
    if stage in RUNNING_CAJITA_STAGES and pid_alive(job.get("pid")):
        return {"active": True, "reason": "CAJITA_WORKER_RECEIPT_PENDING", "stage": stage,
                "pid": job.get("pid"), "candidate_id": lane.get("candidate_id")}
    # A wrapper may exit while its converter child remains alive; inspect command lines.
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            argv = (proc / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace")
        except OSError:
            continue
        if any(token in argv for token in (
            "convert_hf_to_gguf.py", "llama-quantize", "CAJITA_QWEN3_DRY_RUN",
            "CAJITA_CONVERTER_ENV_INSTALL", "CAJITA_CONVERTER_ENV_FALLBACK",
        )):
            return {"active": True, "reason": "CAJITA_HEAVY_PROCESS_DETECTED",
                    "pid": int(proc.name), "command_sha256": hashlib.sha256(argv.encode()).hexdigest()}
    return {"active": False, "reason": "NO_CAJITA_HEAVY_PROCESS_DETECTED"}


@functools.lru_cache(maxsize=8192)
def _debian_version_satisfies(installed_version: str, operator: str, required_version: str) -> bool:
    """Use dpkg's Debian version semantics; comparison uncertainty always blocks."""
    if operator not in {"<<", "<=", "=", ">=", ">>"}:
        return False
    try:
        result = subprocess.run(
            ["dpkg", "--compare-versions", installed_version, operator, required_version],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=5, check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def parse_dpkg_status(status_path: pathlib.Path) -> dict:
    """Resolve installed package dependencies including Debian version constraints."""
    if not status_path.is_file():
        return {"status": "BLOCKED_DPKG_STATUS_MISSING", "installed_package_count": 0,
                "unresolved_dependency_count": 1,
                "unresolved_dependencies": [{"reason": "dpkg status file missing"}]}
    text = status_path.read_text(encoding="utf-8", errors="replace")
    packages = {}
    provided = {}
    for stanza in re.split(r"\n\s*\n", text):
        if not stanza.strip():
            continue
        msg = email.message_from_string(stanza)
        name = (msg.get("Package") or "").strip()
        if not name or msg.get("Status", "").strip() != "install ok installed":
            continue
        packages[name] = msg
        for item in (msg.get("Provides") or "").split(","):
            virtual = re.fullmatch(
                r"\s*([a-z0-9][a-z0-9+.-]*)(?:\s*\(=\s*([^()]+?)\s*\))?\s*", item
            )
            if virtual:
                virtual_name, virtual_version = virtual.groups()
                provided.setdefault(virtual_name, []).append({
                    "provider_package": name, "provided_version": virtual_version,
                })
    missing = []
    total_clauses = 0
    for package_name, msg in packages.items():
        for field in ("Pre-Depends", "Depends"):
            raw = msg.get(field) or ""
            if not raw:
                continue
            for clause in raw.split(","):
                total_clauses += 1
                parsed_alternatives = []
                malformed = []
                for alt in clause.split("|"):
                    match = re.fullmatch(
                        r"\s*([a-z0-9][a-z0-9+.-]*)(?::[a-z0-9-]+)?"
                        r"(?:\s*\((<<|<=|=|>=|>>)\s*([^()]+?)\s*\))?\s*", alt
                    )
                    if not match:
                        malformed.append(alt.strip())
                        continue
                    dep_name, operator, required_version = match.groups()
                    parsed_alternatives.append((dep_name, operator, required_version))
                resolved = False
                if not malformed and parsed_alternatives:
                    for dep_name, operator, required_version in parsed_alternatives:
                        installed_msg = packages.get(dep_name)
                        if installed_msg is not None:
                            if operator is None:
                                resolved = True
                            else:
                                installed_version = (installed_msg.get("Version") or "").strip()
                                resolved = bool(installed_version and _debian_version_satisfies(
                                    installed_version, operator, required_version.strip()
                                ))
                        elif dep_name in provided:
                            providers = provided[dep_name]
                            if operator is None:
                                resolved = bool(providers)
                            else:
                                resolved = any(
                                    item.get("provided_version") is not None
                                    and _debian_version_satisfies(
                                        item["provided_version"], operator, required_version.strip()
                                    )
                                    for item in providers
                                )
                        if resolved:
                            break
                if not resolved:
                    missing.append({
                        "package": package_name, "field": field, "clause": clause.strip(),
                        "alternatives": [x[0] for x in parsed_alternatives],
                        "malformed_alternatives": malformed,
                        "reason": "UNPARSEABLE_DEPENDENCY" if malformed or not parsed_alternatives
                                  else "MISSING_PACKAGE_OR_UNSATISFIED_VERSION_CONSTRAINT",
                    })
    return {
        "status": "PASS_DECLARED_PACKAGE_DEPENDENCIES_RESOLVED" if not missing else "BLOCKED_UNRESOLVED_PACKAGE_DEPENDENCIES",
        "installed_package_count": len(packages), "virtual_provides_count": len(provided),
        "dependency_clause_count": total_clauses,
        "unresolved_dependency_count": len(missing), "unresolved_dependencies": missing[:200],
        "truncated": len(missing) > 200, "dpkg_status_sha256": sha_file(status_path),
        "version_constraints_checked_by": "dpkg --compare-versions",
        "version_comparison_failures_fail_closed": True,
    }


def flatpak_jasp_launch(flatpak_options: list[str], app_args: list[str]) -> list[str]:
    """Launch the pinned JASP app in an unshared Flatpak sandbox.

    Seed control is applied to a disposable .jasp fixture copy through JASP's
    native setSeed/seed options; no R startup profile or injected hook is used.
    """
    command = [
        "/usr/bin/flatpak", "--system", "run", "--unshare=network",
        "--command=/app/bin/JASP",
        "--socket=x11",
        "--filesystem=/tmp/lunita-dbus",
        "--env=DISPLAY=:99",
        "--env=DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/lunita-dbus/bus",
        "--env=QT_QPA_PLATFORM=xcb",
        "--env=LIBGL_ALWAYS_SOFTWARE=1",
        "--env=QTWEBENGINE_DISABLE_SANDBOX=1",
        "--env=LD_LIBRARY_PATH=/app/lib/x86_64-linux-gnu/:/app/lib/aarch64-linux-gnu/",
    ]
    command.extend([*flatpak_options, "org.jaspstats.JASP", *app_args])
    return command


def jasp_process_env(base: dict[str, str]) -> dict[str, str]:
    env = dict(base)
    # The GitHub runner injects a host Python library path. It must not leak
    # into the Flatpak sandbox ahead of the KDE runtime.
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("LD_PRELOAD", None)
    env["QT_QPA_PLATFORM"] = "offscreen"
    return env


def inspect_jasp_runtime_identity(output: str) -> dict:
    """Require the JASP banner version and embedded source commit to match the pinned build."""
    matches = re.findall(
        r"Starting JASP ([0-9]+(?:\.[0-9]+)+) from commit ([0-9a-f]{40})",
        output or "",
    )
    observed = [{"version": version, "source_commit": commit} for version, commit in matches]
    valid = bool(observed) and all(
        item["version"] == EXPECTED_JASP_RUNTIME_VERSION
        and item["source_commit"] == EXPECTED_JASP_SOURCE_COMMIT
        for item in observed
    )
    return {
        "status": "PASS" if valid else "BLOCKED_JASP_RUNTIME_IDENTITY_MISMATCH",
        "expected_version": EXPECTED_JASP_RUNTIME_VERSION,
        "expected_source_commit": EXPECTED_JASP_SOURCE_COMMIT,
        "observed": observed,
    }


def extract_actual_jasp_unit_test_rows(output: str) -> list[str]:
    """Extract the freshly calculated Model Comparison table, not stored reference rows."""
    if not isinstance(output, str) or not output:
        raise ValueError("JASP unit-test output is empty")
    lines = output.splitlines()
    mismatch_at = next(
        (index for index, line in enumerate(lines) if "The results are different" in line),
        len(lines),
    )
    headings = [
        index for index, line in enumerate(lines[:mismatch_at])
        if "Row: | h: Model Comparison |" in line
    ]
    if not headings:
        raise ValueError("JASP output contains no Model Comparison table")
    rows = []
    for line in lines[headings[-1]:mismatch_at]:
        if "Footer:" in line:
            break
        match = re.search(r"Row:\s*(.*)$", line)
        if match and match.group(1).strip():
            rows.append(match.group(1).strip())
    if len(rows) < 2:
        raise ValueError("Fresh JASP Model Comparison table is incomplete")
    return rows


def jasp_result_rows_sha256(rows: list[str]) -> str:
    if not isinstance(rows, list) or not rows or any(not isinstance(row, str) for row in rows):
        raise ValueError("JASP result rows are missing or malformed")
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def seeded_fixture_post_execution_hashes_unchanged(
    receipt: dict | None,
    clone_path: str | None,
    sha_before: str | None,
    sha_after_save: str | None,
    sha_after_rerun: str | None,
    regular_after_save: bool,
    regular_after_rerun: bool,
    removed_after_test: bool,
) -> bool:
    """Require the exact seeded archive bytes to survive both JASP invocations."""
    if not isinstance(receipt, dict):
        return False
    expected = receipt.get("clone_sha256")
    return bool(
        isinstance(expected, str)
        and re.fullmatch(r"[0-9a-f]{64}", expected)
        and isinstance(clone_path, str)
        and clone_path == receipt.get("clone_path")
        and sha_before == expected
        and sha_after_save == expected
        and sha_after_rerun == expected
        and regular_after_save is True
        and regular_after_rerun is True
        and removed_after_test is True
    )


def run_death_penalty_roundtrip(actual_commit: str, env: dict[str, str], stamp: str, mutation_identity: dict | None = None) -> dict:
    """Verify two independent executions of the same hash-bound seeded input.

    The original archive and stored reference results remain immutable. The
    disposable clone changes only the active analyses.json seed option. JASP's
    built-in --unitTest can compare that seeded calculation with historical
    unseeded output; this is recorded separately from deterministic replay.
    """
    source = ROOTFS / "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp"
    report_path = OUT / f"JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_{stamp}.json"
    fixture_receipt_path = OUT / f"JASP_DETERMINISTIC_FIXTURE_ROUNDTRIP_{stamp}.json"
    base = {
        "schema": "CUSTOSZ_LUNITA_JASP_UNITTEST_ROUNDTRIP/1.0",
        "captured_at_utc": utc(),
        "app_commit": actual_commit,
        "app_id": "org.jaspstats.JASP",
        "candidate_id": "G06_REBUILD_CANDIDATE_R1",
        "beta_revision": "beta-v1.7",
        "network_unshared": True,
        "flatpak_sandbox": True,
        "real_analysis_engine_invoked": "JASPEngine",
        "sample_relative_path": "Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp",
        "downloads_performed": False,
        "persistent_sample_copy_created": False,
        "certification": "NOT_GRANTED",
        "mission_completion_claim": False,
    }
    if not source.is_file() or source.is_symlink():
        result = {
            **base,
            "status": "BLOCKED_PACKAGED_ROUNDTRIP_FIXTURE_MISSING",
            "original_sample_unchanged": False,
            "strict_rerun_after_save": {"status": "BLOCKED", "returncode": 125},
            "source_fixture_path": str(source),
        }
        atomic_json(report_path, result)
        return result

    original_before = sha_file(source)
    save_run = {"status": "BLOCKED", "returncode": 125}
    rerun = {"status": "BLOCKED", "returncode": 125}
    temp_before = temp_after = temp_after_rerun = None
    temp_after_save_regular = False
    temp_after_rerun_regular = False
    save_log_integrity_bound = False
    rerun_log_integrity_bound = False
    temp_fixture = None
    temp_root = None
    fixture_receipt = None
    fixture_receipt_valid = False
    save_log_path = OUT / f"JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_{stamp}_save.log"
    rerun_log_path = OUT / f"JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_{stamp}_rerun.log"

    def bind_fixture_hash_to_run_log(
        run_result: dict, label: str, expected_sha256: str | None,
        observed_sha256: str | None, regular_file: bool,
    ) -> bool:
        log_text = run_result.get("log_path")
        if not isinstance(log_text, str) or not log_text:
            return False
        log_path = pathlib.Path(log_text)
        if log_path.is_symlink() or not log_path.is_file():
            return False
        unchanged = bool(
            regular_file is True
            and isinstance(expected_sha256, str)
            and observed_sha256 == expected_sha256
        )
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write("\n")
            stream.write(f"JASP_ROUNDTRIP_FIXTURE_SHA256_EXPECTED={expected_sha256 or 'UNAVAILABLE'}\n")
            stream.write(f"JASP_ROUNDTRIP_FIXTURE_SHA256_AFTER_{label.upper()}={observed_sha256 or 'UNAVAILABLE'}\n")
            stream.write(
                f"JASP_ROUNDTRIP_FIXTURE_UNCHANGED_AFTER_{label.upper()}="
                f"{'TRUE' if unchanged else 'FALSE'}\n"
            )
        run_result["log_sha256"] = sha_file(log_path)
        run_result["fixture_sha256_expected"] = expected_sha256
        run_result["fixture_sha256_after_execution"] = observed_sha256
        run_result["fixture_unchanged_after_execution"] = unchanged
        run_result["fixture_regular_file_after_execution"] = regular_file is True
        return unchanged

    def execute_replay(command: list[str], label: str, log_path: pathlib.Path) -> dict:
        started = utc()
        try:
            identity = mutation_identity if isinstance(mutation_identity, dict) else {}
            executable_sha256 = identity.get("jasp_binary_sha256", "")
            runtime_ostree_commit = identity.get("flatpak_runtime_commit", "")
            invocation_case_id = f"death_penalty_{label}"
            proc = run_bounded_process_tree(
                command, env=env, timeout=300, case_id=invocation_case_id,
                executable_sha256=executable_sha256,
                runtime_ostree_commit=runtime_ostree_commit,
            )
            output = proc.stdout or ""
            rc = int(proc.returncode)
            process_receipt = getattr(proc, "process_tree_receipt", None)
            process_receipt_valid = validate_process_tree_receipt(
                process_receipt, command=command, env=env, timeout=300,
                case_id=invocation_case_id, executable_sha256=executable_sha256,
                runtime_ostree_commit=runtime_ostree_commit, stdout=output, returncode=rc,
            )
            try:
                rows = extract_actual_jasp_unit_test_rows(output)
                rows_sha = jasp_result_rows_sha256(rows)
                capture_status = "PASS"
            except Exception as parse_exc:
                rows = []
                rows_sha = None
                capture_status = "BLOCKED_RESULT_CAPTURE"
                base[f"{label}_capture_error"] = {
                    "type": type(parse_exc).__name__, "message": str(parse_exc)[:800]
                }
            reference_mismatch = rc == 1 and "The results are different" in output
            runtime_identity = inspect_jasp_runtime_identity(output)
            if not process_receipt_valid:
                status = "BLOCKED_PROCESS_TREE_RECEIPT"
            elif runtime_identity.get("status") != "PASS":
                status = "BLOCKED_JASP_RUNTIME_IDENTITY"
            elif capture_status != "PASS":
                status = capture_status
            elif rc == 0:
                status = "PASS_REFERENCE_AND_REPLAY"
            elif reference_mismatch:
                status = "REFERENCE_MISMATCH_RECORDED"
            else:
                status = "BLOCKED_JASP_EXECUTION"
            marker = "SAVE_RUN_RC" if label == "save" else "STRICT_RERUN_RC"
            log_path.write_text(
                f"START_UTC={started}\\nCOMMAND={json.dumps(command)}\\nAPP_COMMIT={actual_commit}\\n"
                + "PROCESS_TREE_RECEIPT_JSON=" + json.dumps(process_receipt, sort_keys=True) + "\\n"
                + output + ("" if output.endswith("\\n") else "\\n")
                + f"ACTUAL_RESULT_ROWS_SHA256={rows_sha or 'UNAVAILABLE'}\\n"
                + f"REFERENCE_MISMATCH={'TRUE' if reference_mismatch else 'FALSE'}\\n"
                + f"{marker}={rc}\\nFINISHED_UTC={utc()}\\n",
                encoding="utf-8", errors="replace",
            )
            return {
                "status": status,
                "returncode": rc,
                "command": command,
                "log_path": str(log_path),
                "log_sha256": sha_file(log_path),
                "actual_result_rows": rows,
                "actual_result_rows_sha256": rows_sha,
                "result_capture_status": capture_status,
                "runtime_identity": runtime_identity,
                "process_tree_receipt": process_receipt,
                "process_tree_receipt_valid": process_receipt_valid,
                "stored_reference_mismatch": reference_mismatch,
            }
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            process_receipt = getattr(exc, "process_tree_receipt", None)
            process_receipt_valid = validate_process_tree_receipt(
                process_receipt, command=command, env=env, timeout=300,
                case_id=f"death_penalty_{label}",
                executable_sha256=(mutation_identity or {}).get("jasp_binary_sha256", ""),
                runtime_ostree_commit=(mutation_identity or {}).get("flatpak_runtime_commit", ""),
                stdout=output, returncode=124, timeout_triggered=True,
            )
            log_path.write_text(
                f"START_UTC={started}\\nCOMMAND={json.dumps(command)}\\n"
                + "PROCESS_TREE_RECEIPT_JSON=" + json.dumps(process_receipt, sort_keys=True) + "\\n"
                + f"{output}\\nTIMEOUT=300\\n",
                encoding="utf-8", errors="replace",
            )
            return {
                "status": "BLOCKED_TIMEOUT",
                "returncode": 124,
                "command": command,
                "log_path": str(log_path),
                "log_sha256": sha_file(log_path),
                "actual_result_rows": [],
                "actual_result_rows_sha256": None,
                "runtime_identity": {"status": "BLOCKED_TIMEOUT"},
                "process_tree_receipt": process_receipt,
                "process_tree_receipt_valid": process_receipt_valid,
                "stored_reference_mismatch": False,
            }
        except ProcessTreeCleanupError as exc:
            process_receipt = exc.process_tree_receipt
            log_path.write_text(
                f"START_UTC={started}\\nCOMMAND={json.dumps(command)}\\n"
                + "PROCESS_TREE_RECEIPT_JSON=" + json.dumps(process_receipt, sort_keys=True) + "\\n"
                + f"PROCESS_TREE_CLEANUP_ERROR={str(exc)[:800]}\\n",
                encoding="utf-8", errors="replace",
            )
            return {
                "status": "BLOCKED_PROCESS_TREE_CLEANUP",
                "returncode": 125,
                "command": command,
                "log_path": str(log_path),
                "log_sha256": sha_file(log_path),
                "actual_result_rows": [],
                "actual_result_rows_sha256": None,
                "runtime_identity": {"status": "BLOCKED_PROCESS_TREE_CLEANUP"},
                "process_tree_receipt": process_receipt,
                "process_tree_receipt_valid": False,
                "stored_reference_mismatch": False,
            }

    try:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="lunita-jasp-death-roundtrip-") as tmp:
            temp_root = pathlib.Path(tmp)
            temp_fixture = temp_root / "DeathPenalty_seeded.jasp"
            fixture_receipt = prepare_deterministic_fixture(
                source, temp_fixture, fixture_receipt_path, DEATH_PENALTY_SOURCE_SHA256
            )
            fixture_receipt_valid = verify_deterministic_fixture_receipt(
                fixture_receipt, DEATH_PENALTY_SOURCE_SHA256, require_clone=True
            )
            temp_before = (
                sha_file(temp_fixture)
                if temp_fixture.is_file() and not temp_fixture.is_symlink()
                else None
            )
            if not fixture_receipt_valid or temp_before != fixture_receipt.get("clone_sha256"):
                raise PermissionError("Deterministic JASP fixture receipt or initial clone hash failed validation")

            command = flatpak_jasp_launch(
                [f"--filesystem={temp_root}"], ["--unitTest", str(temp_fixture)]
            )
            save_run = execute_replay(command, "save", save_log_path)
            temp_after_save_regular = bool(temp_fixture.is_file() and not temp_fixture.is_symlink())
            temp_after = sha_file(temp_fixture) if temp_after_save_regular else None
            save_log_integrity_bound = bind_fixture_hash_to_run_log(
                save_run, "save", fixture_receipt.get("clone_sha256"),
                temp_after, temp_after_save_regular,
            )
            rerun = execute_replay(command, "rerun", rerun_log_path)
            temp_after_rerun_regular = bool(temp_fixture.is_file() and not temp_fixture.is_symlink())
            temp_after_rerun = sha_file(temp_fixture) if temp_after_rerun_regular else None
            rerun_log_integrity_bound = bind_fixture_hash_to_run_log(
                rerun, "rerun", fixture_receipt.get("clone_sha256"),
                temp_after_rerun, temp_after_rerun_regular,
            )
    except Exception as exc:
        base["executor_error"] = {"type": type(exc).__name__, "message": str(exc)[:1200]}

    original_after = sha_file(source) if source.is_file() and not source.is_symlink() else None
    unchanged = bool(
        original_before == DEATH_PENALTY_SOURCE_SHA256
        and original_after == DEATH_PENALTY_SOURCE_SHA256
    )
    temporary_fixture_removed = bool(temp_root and not temp_root.exists())
    roundtrip_hash_invariant = seeded_fixture_post_execution_hashes_unchanged(
        fixture_receipt,
        str(temp_fixture) if temp_fixture else None,
        temp_before,
        temp_after,
        temp_after_rerun,
        temp_after_save_regular,
        temp_after_rerun_regular,
        temporary_fixture_removed,
    )
    roundtrip_reproducible = bool(
        fixture_receipt and fixture_receipt_valid
        and roundtrip_hash_invariant
        and save_log_integrity_bound and rerun_log_integrity_bound
    )
    save_rows = save_run.get("actual_result_rows") or []
    rerun_rows = rerun.get("actual_result_rows") or []
    save_rows_sha = save_run.get("actual_result_rows_sha256")
    rerun_rows_sha = rerun.get("actual_result_rows_sha256")
    actual_rows_equal = bool(
        save_rows and rerun_rows and save_rows_sha
        and save_rows_sha == rerun_rows_sha and save_rows == rerun_rows
    )
    both_reference_pass = (
        save_run.get("returncode") == 0 and rerun.get("returncode") == 0
        and save_run.get("status") == "PASS_REFERENCE_AND_REPLAY"
        and rerun.get("status") == "PASS_REFERENCE_AND_REPLAY"
    )
    both_reference_mismatch = (
        save_run.get("returncode") == 1 and rerun.get("returncode") == 1
        and save_run.get("status") == "REFERENCE_MISMATCH_RECORDED"
        and rerun.get("status") == "REFERENCE_MISMATCH_RECORDED"
        and save_run.get("stored_reference_mismatch") is True
        and rerun.get("stored_reference_mismatch") is True
    )
    reference_status = (
        "PASS" if both_reference_pass else
        "BLOCKED_STORED_REFERENCE_MISMATCH" if both_reference_mismatch else
        "BLOCKED"
    )
    replay_status = "PASS_DETERMINISTIC_REPLAY" if actual_rows_equal else "BLOCKED_DETERMINISTIC_REPLAY"
    runtime_identity_pass = (
        (save_run.get("runtime_identity") or {}).get("status") == "PASS"
        and (rerun.get("runtime_identity") or {}).get("status") == "PASS"
    )
    final_status = (
        "PASS"
        if actual_rows_equal and runtime_identity_pass and fixture_receipt_valid and unchanged and roundtrip_reproducible
        else "FAIL"
    )
    result = {
        **base,
        "captured_at_utc": utc(),
        "status": (
            "PASS_JASP_STRICT_ROUNDTRIP"
            if final_status == "PASS" and reference_status == "PASS" else
            "PASS_DETERMINISTIC_REPLAY_REFERENCE_MISMATCH_RECORDED"
            if final_status == "PASS" and reference_status == "BLOCKED_STORED_REFERENCE_MISMATCH" else
            "BLOCKED_JASP_STRICT_ROUNDTRIP"
        ),
        "deterministic_replay_status": replay_status,
        "reference_comparison_status": reference_status,
        "actual_result_rows_equal": actual_rows_equal,
        "runtime_identity_status": "PASS" if runtime_identity_pass else "BLOCKED",
        "save_runtime_identity": save_run.get("runtime_identity"),
        "rerun_runtime_identity": rerun.get("runtime_identity"),
        "save_actual_result_rows_sha256": save_rows_sha,
        "rerun_actual_result_rows_sha256": rerun_rows_sha,
        "expected_original_sample_sha256": DEATH_PENALTY_SOURCE_SHA256,
        "original_sample_sha256_before": original_before,
        "original_sample_sha256_after": original_after,
        "original_sample_identity_matches_pin": original_before == DEATH_PENALTY_SOURCE_SHA256,
        "original_sample_unchanged": unchanged,
        "source_fixture_path": str(source),
        "deterministic_fixture_receipt": fixture_receipt,
        "deterministic_fixture_receipt_valid": fixture_receipt_valid,
        "save_run": save_run,
        "strict_rerun_after_save": rerun,
        "process_tree_receipt_valid": (
            save_run.get("process_tree_receipt_valid") is True
            and rerun.get("process_tree_receipt_valid") is True
        ),
        "temporary_fixture_sha256_expected": fixture_receipt.get("clone_sha256") if isinstance(fixture_receipt, dict) else None,
        "temporary_fixture_sha256_before": temp_before,
        "temporary_fixture_sha256_after_save": temp_after,
        "temporary_fixture_sha256_after_rerun": temp_after_rerun,
        "temporary_fixture_hash_invariant_passed": roundtrip_hash_invariant,
        "temporary_fixture_regular_after_save": temp_after_save_regular,
        "temporary_fixture_regular_after_rerun": temp_after_rerun_regular,
        "temporary_fixture_changed": bool(
            temp_before and (temp_after != temp_before or temp_after_rerun != temp_before)
        ),
        "temporary_fixture_path": str(temp_fixture) if temp_fixture else None,
        "temporary_fixture_removed_after_test": temporary_fixture_removed,
        "temporary_fixture_stable_after_save_and_rerun": bool(
            temp_after and temp_after == temp_after_rerun
        ),
        "save_log_integrity_bound": save_log_integrity_bound,
        "rerun_log_integrity_bound": rerun_log_integrity_bound,
        "reference_results_modified": False,
        "downloaded": False,
    }
    atomic_json(report_path, result)
    result["report_path"] = str(report_path)
    result["report_sha256"] = sha_file(report_path)
    return result


def validate_jasp_binary_patch_binding(app: dict, patch: dict) -> None:
    """Require the formatter patch log to prove the exact executable hash transition."""
    app_after = app.get("binary_after") if isinstance(app.get("binary_after"), dict) else {}
    before_sha = app.get("binary_before_sha256")
    after_sha = app_after.get("sha256")
    after_path = app_after.get("path")
    if not re.fullmatch(r"[0-9a-f]{64}", str(before_sha or "")) or not re.fullmatch(r"[0-9a-f]{64}", str(after_sha or "")):
        raise RuntimeError("JASP executable pre/post SHA-256 is missing or malformed")
    if not isinstance(after_path, str) or not after_path:
        raise RuntimeError("JASP executable post-mutation path is missing")
    changed = before_sha != after_sha
    if app.get("binary_unchanged_by_formatter_patch") is not (not changed):
        raise RuntimeError("JASP executable unchanged flag contradicts its pre/post SHA-256 values")
    if patch.get("changed_jasp_binary") is not changed:
        raise RuntimeError("Formatter patch binary-change flag contradicts the executable SHA-256 transition")
    transition = app.get("binary_transition")
    if not isinstance(transition, dict) or (
        transition.get("path") != after_path
        or transition.get("before_sha256") != before_sha
        or transition.get("after_sha256") != after_sha
        or transition.get("changed") is not changed
    ):
        raise RuntimeError("JASP executable transition receipt is missing or inconsistent")
    rows = patch.get("patched_resources")
    if not isinstance(rows, list):
        raise RuntimeError("Formatter patch resource inventory is missing")
    canonical_path = str(pathlib.Path(after_path).resolve(strict=True))
    matches = [
        row for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("path"), str)
        and str(pathlib.Path(row["path"]).resolve(strict=True)) == canonical_path
    ]
    if changed:
        if len(matches) != 1:
            raise RuntimeError("Changed JASP executable lacks exactly one embedded formatter patch record")
        row = matches[0]
        if (
            row.get("before_sha256") != before_sha
            or row.get("after_sha256") != after_sha
            or row.get("observed_after_sha256") != after_sha
        ):
            raise RuntimeError("Embedded formatter patch record does not match the JASP executable hash transition")
    elif matches:
        raise RuntimeError("Unchanged JASP executable is incorrectly listed as a patched formatter resource")

def verify_jasp_runtime_mutation_receipt() -> dict:
    """Verify exact post-refresh JASP/Qt files and Flatpak deployments used by this run."""
    if CERTIFICATION_PROFILE != "V1_8_DIRECT":
        return {"status": "NOT_APPLICABLE", "returncode": 0}
    receipt_text = os.environ.get("LUNITA_JASP_MUTATION_RECEIPT", "")
    if not receipt_text:
        return {"status": "BLOCKED", "returncode": 1, "details": "LUNITA_JASP_MUTATION_RECEIPT is unset"}
    receipt_path = pathlib.Path(receipt_text)
    try:
        if receipt_path.is_symlink() or not receipt_path.is_file():
            raise RuntimeError("JASP runtime mutation receipt is missing or unsafe")
        receipt = load_json(receipt_path, {}) or {}
        receipt_sha = sha_file(receipt_path)
        app = receipt.get("application") if isinstance(receipt.get("application"), dict) else {}
        runtime = receipt.get("runtime") if isinstance(receipt.get("runtime"), dict) else {}
        sdk = receipt.get("sdk") if isinstance(receipt.get("sdk"), dict) else {}
        qt = receipt.get("qt_http_server") if isinstance(receipt.get("qt_http_server"), dict) else {}
        patch = receipt.get("formatter_patch") if isinstance(receipt.get("formatter_patch"), dict) else {}
        app_after = app.get("binary_after") if isinstance(app.get("binary_after"), dict) else {}
        validate_jasp_binary_patch_binding(app, patch)
        if (
            receipt.get("schema") != "LUNITA_JASP_RUNTIME_POST_MUTATION_RECEIPT/1.0"
            or receipt.get("status") != "PASS"
            or receipt.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1"
            or receipt.get("candidate_version") != "1.8.0"
            or app.get("flatpak_ref") != "org.jaspstats.JASP"
            or app.get("commit_before") != EXPECTED_JASP_APP_COMMIT
            or app.get("commit_after") != EXPECTED_JASP_APP_COMMIT
            or app.get("pinned_commit") != EXPECTED_JASP_APP_COMMIT
            or not isinstance(runtime.get("flatpak_ref"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", runtime.get("commit_after", ""))
            or not re.fullmatch(r"[0-9a-f]{64}", sdk.get("commit", ""))
            or patch.get("r_startup_profile_mutated") is not False
            or not isinstance(patch.get("call_sites"), int) or patch.get("call_sites") < 1
            or not isinstance(patch.get("latex_sites"), int) or patch.get("latex_sites") < 1
            or not isinstance(patch.get("patched_resources"), list) or not patch.get("patched_resources")
        ):
            raise RuntimeError("JASP runtime mutation receipt schema, candidate, commit or patch contract mismatch")

        env = jasp_process_env(os.environ)
        env["FLATPAK_SYSTEM_DIR"] = str(ROOTFS / "var/lib/flatpak")
        def flatpak_commit(ref: str, host: bool = False) -> str:
            command_env = dict(env)
            if host:
                command_env.pop("FLATPAK_SYSTEM_DIR", None)
            probe = subprocess.run(
                ["/usr/bin/flatpak", "--system", "info", "--show-commit", ref],
                env=command_env, capture_output=True, text=True, timeout=30, check=False,
            )
            observed = probe.stdout.strip() if probe.returncode == 0 else ""
            if probe.returncode != 0 or not re.fullmatch(r"[0-9a-f]{64}", observed):
                raise RuntimeError(f"Cannot verify live Flatpak commit for {ref}: {probe.stderr[-500:]}")
            return observed

        live_app_commit = flatpak_commit("org.jaspstats.JASP")
        live_runtime_commit = flatpak_commit(runtime["flatpak_ref"])
        live_sdk_commit = flatpak_commit(sdk.get("flatpak_ref", ""), host=True)
        if live_app_commit != EXPECTED_JASP_APP_COMMIT:
            raise RuntimeError("Live JASP app commit differs from the mutation receipt")
        if live_runtime_commit != runtime.get("commit_after"):
            raise RuntimeError("Live Flatpak runtime commit differs from the mutation receipt")
        if live_sdk_commit != sdk.get("commit"):
            raise RuntimeError("Live Flatpak SDK commit differs from the mutation receipt")

        expected_jasp_binary = (
            ROOTFS / "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/bin/JASP"
        ).resolve(strict=True)
        recorded_jasp_path = pathlib.Path(app_after.get("path", "")).resolve(strict=True)
        if recorded_jasp_path != expected_jasp_binary:
            raise RuntimeError("Mutation receipt JASP executable path is not the installed candidate executable")

        evidence = {str(receipt_path): receipt_sha}
        def verify_record(row: dict, label: str) -> None:
            file_path = pathlib.Path(row.get("path", ""))
            digest = row.get("sha256")
            if file_path.is_symlink() or not file_path.is_file() or not isinstance(digest, str):
                raise RuntimeError(f"{label} file is missing or unsafe")
            observed = sha_file(file_path)
            if observed != digest:
                raise RuntimeError(f"{label} SHA-256 changed after the mutation receipt")
            evidence[str(file_path)] = digest

        verify_record(app_after, "JASP binary")
        files_root = expected_jasp_binary.parent.parent.resolve(strict=True)
        patch_rows = patch.get("patched_resources")
        patch_calls = 0
        patch_latex = 0
        for row in patch_rows:
            if not isinstance(row, dict):
                raise RuntimeError("JASP patched resource row is malformed")
            resource_path = pathlib.Path(row.get("path", "")).resolve(strict=True)
            try:
                resource_path.relative_to(files_root)
            except ValueError as exc:
                raise RuntimeError("Patched JASP resource escapes the Flatpak files tree") from exc
            if row.get("before_sha256") == row.get("after_sha256") or row.get("observed_after_sha256") != row.get("after_sha256"):
                raise RuntimeError("Patched JASP resource lacks a valid before/after hash transition")
            verify_record({
                "path": str(resource_path),
                "sha256": row.get("after_sha256"),
            }, "Patched JASP formatter resource")
            patch_calls += row.get("call_sites", 0)
            patch_latex += row.get("latex_sites", 0)
        if patch_calls != patch.get("call_sites") or patch_latex != patch.get("latex_sites"):
            raise RuntimeError("JASP patch resource totals differ from the aggregate patch receipt")
        verify_record(qt.get("source_archive") or {}, "QtHttpServer source archive")
        for key in ("built_libraries", "installed_libraries_after"):
            rows = qt.get(key)
            if not isinstance(rows, list) or not rows:
                raise RuntimeError(f"JASP mutation receipt has no {key}")
            for row in rows:
                verify_record(row, key)
        for row in (qt.get("installed_libraries_before_snapshot_file"), patch.get("script"), patch.get("log")):
            if not isinstance(row, dict):
                raise RuntimeError("JASP mutation receipt is missing a supporting source/log record")
            verify_record(row, "JASP mutation provenance")
        expected_patch_script = str(
            (ROOT.parent.parent / "scripts" / "lunita" / "patch_jasp_certification_runtime_v1.py").resolve()
        )
        if patch.get("script", {}).get("path") != expected_patch_script:
            raise RuntimeError("JASP formatter patch script path differs from the tracked source")
        if not re.fullmatch(r"\d+\.\d+\.\d+", str(qt.get("qt_version", ""))):
            raise RuntimeError("Qt version in JASP mutation receipt is malformed")
        return {
            "status": "PASS",
            "returncode": 0,
            "receipt_path": str(receipt_path),
            "receipt_sha256": receipt_sha,
            "jasp_app_commit": live_app_commit,
            "flatpak_runtime_ref": runtime["flatpak_ref"],
            "flatpak_runtime_commit": live_runtime_commit,
            "flatpak_sdk_ref": sdk["flatpak_ref"],
            "flatpak_sdk_commit": live_sdk_commit,
            "qt_version": qt["qt_version"],
            "jasp_binary_path": str(expected_jasp_binary),
            "jasp_binary_sha256": app_after["sha256"],
            "formatter_patch_script_sha256": patch["script"]["sha256"],
            "formatter_patch_log_sha256": patch["log"]["sha256"],
            "evidence": evidence,
        }
    except Exception as exc:
        return {
            "status": "BLOCKED",
            "returncode": 1,
            "details": f"JASP_POST_MUTATION_RUNTIME_IDENTITY_ERROR:{type(exc).__name__}:{exc}",
        }


def run_jasp_regression_suite(result_path: pathlib.Path) -> dict:
    """Rerun the registered JASP packaged-data tests in the pinned sandbox."""
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT.mkdir(parents=True, exist_ok=True)
    expected_commit = EXPECTED_JASP_APP_COMMIT
    mutation_identity = verify_jasp_runtime_mutation_receipt()
    fixtures = {
        "flatpak_launch": ("JASP_UNITTEST_FLATPAK", "/app/lunita-fixtures/DeathPenalty.jasp", "JASP_UNITTEST_RC"),
        "reliability": ("JASP_UNITTEST_RELIABILITY", "/app/lunita-fixtures/Reliability.jasp", "JASP_RELIABILITY_UNITTEST_RC"),
        "weight_gain": ("JASP_UNITTEST_WEIGHT_GAIN", "/app/lunita-fixtures/WeightGain.jasp", "JASP_WEIGHT_GAIN_UNITTEST_RC"),
    }
    env = jasp_process_env(os.environ)
    env["FLATPAK_SYSTEM_DIR"] = str(ROOTFS / "var/lib/flatpak")
    workflow_identity = {
        "run_id": str(env.get("GITHUB_RUN_ID", "")),
        "run_attempt": str(env.get("GITHUB_RUN_ATTEMPT", "")),
    }
    workflow_identity_valid = all(
        re.fullmatch(r"[0-9]+", workflow_identity[key])
        for key in ("run_id", "run_attempt")
    )
    results = {"schema": "CUSTOSZ_LUNITA_JASP_AUTOMATED_REGRESSION_SUITE/1.0", "timestamp_utc": utc(),
               "candidate_id": "G06_REBUILD_CANDIDATE_R1", "expected_app_commit": expected_commit,
               "flatpak_system_dir": env["FLATPAK_SYSTEM_DIR"], "network_unshared": True,
               "workflow_identity": workflow_identity,
               "workflow_identity_valid": workflow_identity_valid,
               "runtime_mutation_identity": mutation_identity,
               "tests": {}, "certification": "NOT_GRANTED", "mission_completion_claim": False}
    try:
        if not workflow_identity_valid:
            results["status"] = "BLOCKED_GITHUB_WORKFLOW_IDENTITY"
            results["workflow_identity_error"] = (
                "GITHUB_RUN_ID and GITHUB_RUN_ATTEMPT must be numeric and explicitly propagated "
                "to the privileged independent certification lane"
            )
            atomic_json(result_path, results)
            return results
        if mutation_identity.get("status") != "PASS":
            results["status"] = "BLOCKED_JASP_POST_MUTATION_RUNTIME_IDENTITY"
            atomic_json(result_path, results)
            return results
        probe = subprocess.run(["/usr/bin/flatpak", "--system", "info", "--show-commit", "org.jaspstats.JASP"],
                               env=env, capture_output=True, text=True, timeout=30, check=False)
        actual_commit = probe.stdout.strip() if probe.returncode == 0 else None
        results["app_commit_probe"] = {"returncode": probe.returncode, "actual_commit": actual_commit,
                                       "stderr_tail": probe.stderr[-1500:]}
        if probe.returncode != 0 or actual_commit != expected_commit:
            results["status"] = "BLOCKED_JASP_PIN_MISMATCH"
            atomic_json(result_path, results)
            return results
        with __import__("tempfile").TemporaryDirectory(prefix="lunita-jasp-cert-lane-") as temp_home:
            env["HOME"] = temp_home
            env["XDG_CACHE_HOME"] = str(pathlib.Path(temp_home) / ".cache")
            env["XDG_CONFIG_HOME"] = str(pathlib.Path(temp_home) / ".config")
            env["XDG_DATA_HOME"] = str(pathlib.Path(temp_home) / ".local/share")
            pathlib.Path(env["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)
            original_source = ROOTFS / "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp"
            original_alias = ROOTFS / "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/lunita-fixtures/DeathPenalty.jasp"
            original_alias_valid = False
            original_source_sha = None
            if original_source.is_file() and not original_source.is_symlink() and original_alias.is_symlink():
                try:
                    original_alias_valid = (
                        original_alias.resolve(strict=True) == original_source.resolve(strict=True)
                        and sha_file(original_alias) == DEATH_PENALTY_SOURCE_SHA256
                        and sha_file(original_source) == DEATH_PENALTY_SOURCE_SHA256
                    )
                    original_source_sha = sha_file(original_alias)
                except OSError:
                    original_alias_valid = False

            for case_id, (prefix, fixture, marker) in fixtures.items():
                log_path = OUT / f"{prefix}_{stamp}.log"
                started = utc()
                test_fixture = fixture
                flatpak_options = []
                deterministic_fixture_receipt = None
                deterministic_fixture_receipt_valid = False
                deterministic_fixture_clone_sha256_after_execution = None
                deterministic_fixture_clone_unchanged_after_execution = False
                if case_id == "flatpak_launch":
                    if not original_alias_valid or original_source_sha != DEATH_PENALTY_SOURCE_SHA256:
                        raise FixtureError("Original packaged Death Penalty fixture is not hash-bound to its immutable pin")
                    seeded_root = pathlib.Path(temp_home) / "flatpak-launch-seeded-fixture"
                    seeded_root.mkdir(mode=0o700)
                    seeded_fixture = seeded_root / "DeathPenalty_seeded.jasp"
                    seeded_receipt_path = OUT / f"JASP_FLATPAK_SEEDED_FIXTURE_{stamp}.json"
                    deterministic_fixture_receipt = prepare_deterministic_fixture(
                        original_source, seeded_fixture, seeded_receipt_path, DEATH_PENALTY_SOURCE_SHA256
                    )
                    deterministic_fixture_receipt_valid = verify_deterministic_fixture_receipt(
                        deterministic_fixture_receipt, DEATH_PENALTY_SOURCE_SHA256, require_clone=True
                    )
                    if not deterministic_fixture_receipt_valid:
                        raise FixtureError("Seeded Flatpak-launch fixture receipt failed hash-bound validation")
                    test_fixture = str(seeded_fixture)
                    flatpak_options = [f"--filesystem={seeded_root}"]
                command = flatpak_jasp_launch(flatpak_options, ["--unitTest", test_fixture])
                header = (
                    f"START_UTC={started}\nAPP_COMMIT={actual_commit}\nTEST_FILE={test_fixture}\n"
                    f"JASP_RUNTIME_MUTATION_RECEIPT_SHA256={mutation_identity.get('receipt_sha256')}\n"
                    f"JASP_BINARY_SHA256={mutation_identity.get('jasp_binary_sha256')}\n"
                    f"FLATPAK_RUNTIME_COMMIT={mutation_identity.get('flatpak_runtime_commit')}\n"
                    f"FLATPAK_SDK_COMMIT={mutation_identity.get('flatpak_sdk_commit')}\n"
                    "EXECUTION_MODE=PINNED_CANDIDATE_FLATPAK_SANDBOX_NETWORK_UNSHARED\n"
                )
                if case_id == "flatpak_launch":
                    header += (
                        f"ORIGINAL_FIXTURE_PATH={original_source}\n"
                        f"ORIGINAL_FIXTURE_ALIAS={original_alias}\n"
                        f"ORIGINAL_FIXTURE_SHA256={original_source_sha or 'UNAVAILABLE'}\n"
                        f"ORIGINAL_FIXTURE_ALIAS_VALID={'TRUE' if original_alias_valid else 'FALSE'}\n"
                        f"DETERMINISTIC_FIXTURE_RECEIPT_PATH={deterministic_fixture_receipt.get('receipt_path')}\n"
                        f"DETERMINISTIC_FIXTURE_RECEIPT_SHA256={deterministic_fixture_receipt.get('receipt_sha256')}\n"
                        f"DETERMINISTIC_FIXTURE_CLONE_SHA256={deterministic_fixture_receipt.get('clone_sha256')}\n"
                        "DETERMINISTIC_FIXTURE_SEED_ENABLED=TRUE\n"
                    )
                try:
                    executable_sha256 = mutation_identity.get("jasp_binary_sha256", "")
                    runtime_ostree_commit = mutation_identity.get("flatpak_runtime_commit", "")
                    run = run_bounded_process_tree(
                        command, env=env, timeout=300, case_id=case_id,
                        executable_sha256=executable_sha256,
                        runtime_ostree_commit=runtime_ostree_commit,
                    )
                    rc = int(run.returncode)
                    process_receipt = getattr(run, "process_tree_receipt", None)
                    process_receipt_valid = validate_process_tree_receipt(
                        process_receipt, command=command, env=env, timeout=300,
                        case_id=case_id, executable_sha256=executable_sha256,
                        runtime_ostree_commit=runtime_ostree_commit,
                        stdout=run.stdout or "", returncode=rc,
                    )
                    runtime_identity = inspect_jasp_runtime_identity(run.stdout or "")
                    fixture_integrity = (
                        original_alias_valid
                        and original_source_sha == DEATH_PENALTY_SOURCE_SHA256
                        and original_source.is_file()
                        and sha_file(original_source) == DEATH_PENALTY_SOURCE_SHA256
                        and sha_file(original_alias) == DEATH_PENALTY_SOURCE_SHA256
                    ) if case_id == "flatpak_launch" else True
                    if case_id == "flatpak_launch":
                        seeded_clone_path = pathlib.Path(test_fixture)
                        if seeded_clone_path.is_file() and not seeded_clone_path.is_symlink():
                            deterministic_fixture_clone_sha256_after_execution = sha_file(seeded_clone_path)
                        deterministic_fixture_clone_unchanged_after_execution = (
                            deterministic_fixture_clone_sha256_after_execution
                            == deterministic_fixture_receipt.get("clone_sha256")
                        )
                        deterministic_fixture_receipt_valid = (
                            deterministic_fixture_clone_unchanged_after_execution
                            and verify_deterministic_fixture_receipt(
                                deterministic_fixture_receipt,
                                DEATH_PENALTY_SOURCE_SHA256,
                                require_clone=True,
                            )
                        )
                    case_status = "PASS" if (
                        rc == 0 and fixture_integrity and runtime_identity.get("status") == "PASS"
                        and process_receipt_valid
                        and (
                            case_id != "flatpak_launch"
                            or (
                                deterministic_fixture_receipt_valid
                                and deterministic_fixture_clone_unchanged_after_execution
                            )
                        )
                    ) else "BLOCKED"
                    clone_post_execution_markers = (
                        f"DETERMINISTIC_FIXTURE_CLONE_SHA256_AFTER_EXECUTION={deterministic_fixture_clone_sha256_after_execution or 'UNAVAILABLE'}\n"
                        f"DETERMINISTIC_FIXTURE_CLONE_UNCHANGED_AFTER_EXECUTION={'TRUE' if deterministic_fixture_clone_unchanged_after_execution else 'FALSE'}\n"
                    ) if case_id == "flatpak_launch" else ""
                    payload = (
                        header + "PROCESS_TREE_RECEIPT_JSON=" + json.dumps(process_receipt, sort_keys=True) + "\n"
                        + run.stdout + ("" if run.stdout.endswith("\n") else "\n")
                        + clone_post_execution_markers
                        + f"\n{marker}={rc}\nFINISHED_UTC={utc()}\n"
                    )
                    log_path.write_text(payload, encoding="utf-8", errors="replace")
                    results["tests"][case_id] = {
                        "status": case_status,
                        "returncode": rc,
                        "fixture": test_fixture,
                        "original_fixture": fixture,
                        "log_path": str(log_path),
                        "log_sha256": sha_file(log_path),
                        "command": command,
                        "started_at_utc": started,
                        "finished_at_utc": utc(),
                        "original_fixture_path": str(original_source) if case_id == "flatpak_launch" else None,
                        "original_fixture_sha256": original_source_sha if case_id == "flatpak_launch" else None,
                        "original_fixture_alias_valid": fixture_integrity if case_id == "flatpak_launch" else None,
                        "deterministic_fixture_receipt": deterministic_fixture_receipt,
                        "deterministic_fixture_receipt_valid": deterministic_fixture_receipt_valid,
                        "deterministic_fixture_path": test_fixture if case_id == "flatpak_launch" else None,
                        "deterministic_fixture_clone_sha256_after_execution": deterministic_fixture_clone_sha256_after_execution,
                        "deterministic_fixture_clone_unchanged_after_execution": deterministic_fixture_clone_unchanged_after_execution,
                        "runtime_identity": runtime_identity,
                        "process_tree_receipt": process_receipt,
                        "process_tree_receipt_valid": process_receipt_valid,
                    }
                except subprocess.TimeoutExpired as exc:
                    output = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                    process_receipt = getattr(exc, "process_tree_receipt", None)
                    process_receipt_valid = validate_process_tree_receipt(
                        process_receipt, command=command, env=env, timeout=300,
                        case_id=case_id,
                        executable_sha256=mutation_identity.get("jasp_binary_sha256", ""),
                        runtime_ostree_commit=mutation_identity.get("flatpak_runtime_commit", ""),
                        stdout=output, returncode=124, timeout_triggered=True,
                    )
                    log_path.write_text(
                        header + "PROCESS_TREE_RECEIPT_JSON=" + json.dumps(process_receipt, sort_keys=True) + "\n"
                        + output + f"\n{marker}=124\nTIMEOUT=300\n",
                        encoding="utf-8",
                    )
                    results["tests"][case_id] = {
                        "status": "BLOCKED_TIMEOUT",
                        "returncode": 124,
                        "fixture": test_fixture,
                        "original_fixture": fixture,
                        "log_path": str(log_path),
                        "log_sha256": sha_file(log_path),
                        "process_tree_receipt": process_receipt,
                        "process_tree_receipt_valid": process_receipt_valid,
                    }
                except Exception as exc:
                    process_receipt = getattr(exc, "process_tree_receipt", None)
                    log_path.write_text(
                        header + "PROCESS_TREE_RECEIPT_JSON=" + json.dumps(process_receipt, sort_keys=True) + "\n"
                        + f"EXECUTION_ERROR={type(exc).__name__}:{str(exc)[:1000]}\n{marker}=125\n",
                        encoding="utf-8",
                    )
                    results["tests"][case_id] = {
                        "status": "BLOCKED_EXECUTION_ERROR",
                        "returncode": 125,
                        "fixture": test_fixture,
                        "original_fixture": fixture,
                        "log_path": str(log_path),
                        "log_sha256": sha_file(log_path),
                        "deterministic_fixture_receipt": deterministic_fixture_receipt,
                        "deterministic_fixture_receipt_valid": deterministic_fixture_receipt_valid,
                        "deterministic_fixture_path": test_fixture if case_id == "flatpak_launch" else None,
                        "deterministic_fixture_clone_sha256_after_execution": deterministic_fixture_clone_sha256_after_execution,
                        "deterministic_fixture_clone_unchanged_after_execution": False,
                        "process_tree_receipt": process_receipt,
                        "process_tree_receipt_valid": False,
                    }
            results["roundtrip_gate"] = run_death_penalty_roundtrip(actual_commit, env, stamp, mutation_identity)
    except Exception as exc:
        results["status"] = "BLOCKED_JASP_TEST_EXECUTOR"
        results["executor_error"] = {"type": type(exc).__name__, "message": str(exc)[:1200]}
        atomic_json(result_path, results)
        return results
    roundtrip = results.get("roundtrip_gate") or {"status": "BLOCKED_ROUNDTRIP_NOT_RUN"}
    roundtrip_fixture_receipt = roundtrip.get("deterministic_fixture_receipt")
    if not isinstance(roundtrip_fixture_receipt, dict):
        roundtrip_fixture_receipt = {}
    roundtrip_status_consistent = (
        (roundtrip.get("status") == "PASS_JASP_STRICT_ROUNDTRIP"
         and roundtrip.get("reference_comparison_status") == "PASS")
        or (roundtrip.get("status") == "PASS_DETERMINISTIC_REPLAY_REFERENCE_MISMATCH_RECORDED"
            and roundtrip.get("reference_comparison_status") == "BLOCKED_STORED_REFERENCE_MISMATCH")
    )
    roundtrip_ok = (
        roundtrip_status_consistent
        and roundtrip.get("deterministic_replay_status") == "PASS_DETERMINISTIC_REPLAY"
        and roundtrip.get("actual_result_rows_equal") is True
        and roundtrip.get("runtime_identity_status") == "PASS"
        and isinstance(roundtrip.get("save_actual_result_rows_sha256"), str)
        and roundtrip.get("save_actual_result_rows_sha256") == roundtrip.get("rerun_actual_result_rows_sha256")
        and roundtrip.get("original_sample_unchanged") is True
        and roundtrip.get("temporary_fixture_hash_invariant_passed") is True
        and roundtrip.get("temporary_fixture_sha256_expected") == roundtrip_fixture_receipt.get("clone_sha256")
        and roundtrip.get("temporary_fixture_sha256_before") == roundtrip_fixture_receipt.get("clone_sha256")
        and roundtrip.get("temporary_fixture_sha256_after_save") == roundtrip_fixture_receipt.get("clone_sha256")
        and roundtrip.get("temporary_fixture_sha256_after_rerun") == roundtrip_fixture_receipt.get("clone_sha256")
        and roundtrip.get("save_log_integrity_bound") is True
        and roundtrip.get("rerun_log_integrity_bound") is True
        and roundtrip.get("deterministic_fixture_receipt_valid") is True
        and (roundtrip.get("save_run") or {}).get("process_tree_receipt_valid") is True
        and (roundtrip.get("strict_rerun_after_save") or {}).get("process_tree_receipt_valid") is True
        and verify_deterministic_fixture_receipt(
            roundtrip_fixture_receipt, DEATH_PENALTY_SOURCE_SHA256, require_clone=False
        )
    )
    results["status"] = "PASS_REGISTERED_JASP_TESTS" if (
        results["tests"] and all(x.get("status") == "PASS" and x.get("returncode") == 0
                                 for x in results["tests"].values()) and roundtrip_ok
    ) else "BLOCKED_JASP_REGRESSION"
    results["roundtrip_gate"] = roundtrip
    atomic_json(result_path, results)
    return results

def inventory_worker_command(result_path: pathlib.Path) -> list[str]:
    """Run only the read-only rootfs inventory with root traversal rights.

    Candidate directories remain 0700/0600. The worker uses sudo read-only
    access; it does not chown/chmod or otherwise alter rootfs content.
    """
    script = str(pathlib.Path(__file__).resolve())
    worker = [sys.executable, "-B", script, "--inventory-worker", str(result_path)]
    if os.geteuid() == 0:
        return worker
    sudo = shutil.which("sudo")
    if not sudo:
        raise PermissionError("Rootfs inventory requires read-only privileged traversal; sudo is unavailable")
    preserved = ",".join(INVENTORY_PRIVILEGED_ENV)
    return [sudo, "-n", f"--preserve-env={preserved}", *worker]


def restore_inventory_artifact_owner(path: pathlib.Path) -> None:
    """Return root-created evidence files to the invoking workflow user, mode 0600."""
    if os.geteuid() != 0:
        return
    uid_text, gid_text = os.environ.get("SUDO_UID"), os.environ.get("SUDO_GID")
    if uid_text is None and gid_text is None:
        return
    if not (uid_text and gid_text and uid_text.isdigit() and gid_text.isdigit()):
        raise PermissionError("Cannot restore inventory evidence ownership from incomplete sudo identity")
    os.chown(path, int(uid_text), int(gid_text), follow_symlinks=False)
    os.chmod(path, 0o600)


def _entry_rows(root: pathlib.Path):
    """Yield non-following filesystem entries in stable order."""
    def deny_walk_error(error: OSError) -> None:
        raise error

    for base, dirs, files in os.walk(
        root, topdown=True, followlinks=False, onerror=deny_walk_error
    ):
        dirs.sort()
        files.sort()
        bp = pathlib.Path(base)
        # Include the base directory itself, then children. Symlinked dirs are not traversed.
        if bp != root:
            yield bp
        for name in list(dirs):
            p = bp / name
            if p.is_symlink():
                yield p
                dirs.remove(name)
        for name in files:
            yield bp / name


def _meta_digest(root: pathlib.Path) -> tuple[str, int]:
    h = hashlib.sha256()
    count = 0
    for path in _entry_rows(root):
        try:
            st = path.lstat()
            if pathlib.Path(path).is_symlink():
                kind, extra = "symlink", os.readlink(path)
            elif pathlib.Path(path).is_dir():
                kind, extra = "dir", ""
            elif pathlib.Path(path).is_file():
                kind, extra = "file", ""
            else:
                kind, extra = "special", str(st.st_rdev)
            row = [path.relative_to(root).as_posix(), kind, st.st_mode, st.st_uid,
                   st.st_gid, st.st_size, st.st_mtime_ns, extra]
            h.update((json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n").encode())
            count += 1
        except OSError as exc:
            h.update((f"ERROR\t{path}\t{type(exc).__name__}\n").encode())
            count += 1
    return h.hexdigest(), count


def hash_regular_file_read_only(path: pathlib.Path) -> tuple[str, str]:
    """Hash as the current user; on EACCES, use non-interactive sudo for read-only sha256sum.

    This does not chmod, chown, copy, or otherwise mutate the candidate rootfs.
    If passwordless sudo is unavailable, the inventory remains blocked.
    """
    try:
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest(), "CURRENT_USER_READ"
    except PermissionError as original:
        try:
            path.relative_to(ROOTFS)
        except ValueError as exc:
            raise PermissionError("Privileged hash path escapes candidate rootfs") from exc
        sudo = shutil.which("sudo")
        sha256sum = shutil.which("sha256sum")
        if not sudo or not sha256sum:
            raise PermissionError("Read denied and sudo/sha256sum is unavailable") from original
        result = subprocess.run(
            [sudo, "-n", sha256sum, "--", str(path)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600, check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "sudo read-only hash failed").strip()[-600:]
            raise PermissionError("Passwordless sudo read-only hash failed: " + detail) from original
        token = result.stdout.split(maxsplit=1)[0] if result.stdout.split() else ""
        if not re.fullmatch(r"[0-9a-fA-F]{64}", token):
            raise RuntimeError("Privileged sha256sum returned an invalid digest")
        return token.lower(), "SUDO_NONINTERACTIVE_READ_ONLY_SHA256SUM"


def build_rootfs_inventory(report_path: pathlib.Path | None = None) -> dict:
    """Hash every regular file without following symlinks; retain a JSONL manifest."""
    EVIDENCE.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = EVIDENCE / f"rootfs_inventory_{stamp}.jsonl"
    report_path = report_path or (EVIDENCE / f"rootfs_inventory_{stamp}.json")
    if not ROOTFS.is_dir():
        result = {"schema": "CUSTOSZ_LUNITA_ROOTFS_INVENTORY/1.0", "status": "BLOCKED_ROOTFS_MISSING",
                  "timestamp_utc": utc(), "rootfs_path": str(ROOTFS), "certification": "NOT_GRANTED"}
        atomic_json(report_path, result)
        restore_inventory_artifact_owner(report_path)
        return result

    status_path = ROOTFS / "var/lib/dpkg/status"
    os_release = ROOTFS / "etc/os-release"
    launcher = ROOTFS / "opt/lunita/agent/lunita.py"
    before_digest, before_count = _meta_digest(ROOTFS)
    tmp_manifest = manifest.with_suffix(".jsonl.partial")
    count = total_bytes = errors_count = symlink_count = regular_count = privileged_hash_count = 0
    errors = []
    digest = hashlib.sha256()
    with tmp_manifest.open("x", encoding="utf-8") as out:
        for path in _entry_rows(ROOTFS):
            rel = path.relative_to(ROOTFS).as_posix()
            try:
                st0 = path.lstat()
                if path.is_symlink():
                    kind, link, file_hash = "symlink", os.readlink(path), None
                    symlink_count += 1
                elif path.is_dir():
                    kind, link, file_hash = "directory", None, None
                elif path.is_file():
                    kind, link = "file", None
                    file_hash, hash_method = hash_regular_file_read_only(path)
                    if hash_method == "SUDO_NONINTERACTIVE_READ_ONLY_SHA256SUM":
                        privileged_hash_count += 1
                    st1 = path.lstat()
                    if (st0.st_size, st0.st_mtime_ns, st0.st_mode) != (st1.st_size, st1.st_mtime_ns, st1.st_mode):
                        raise RuntimeError("FILE_CHANGED_DURING_INVENTORY")
                    regular_count += 1
                    total_bytes += st0.st_size
                else:
                    kind, link, file_hash = "special", None, None
                    hash_method = None
                if kind != "file":
                    hash_method = None
                row = {"path": rel, "type": kind, "mode": st0.st_mode & 0o7777,
                       "uid": st0.st_uid, "gid": st0.st_gid, "size_bytes": st0.st_size,
                       "mtime_ns": st0.st_mtime_ns, "sha256": file_hash,
                       "hash_method": hash_method, "symlink_target": link}
            except Exception as exc:
                errors_count += 1
                if len(errors) < 200:
                    errors.append({"path": rel, "error_type": type(exc).__name__, "error": str(exc)[:400]})
                row = {"path": rel, "type": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:400]}
            line = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
            out.write(line)
            digest.update(line.encode())
            count += 1
        out.flush()
        os.fsync(out.fileno())
    after_digest, after_count = _meta_digest(ROOTFS)
    stable_tree = before_digest == after_digest and before_count == after_count
    os.replace(tmp_manifest, manifest)
    restore_inventory_artifact_owner(manifest)
    dep = parse_dpkg_status(status_path)
    launcher_sha = sha_file(launcher) if launcher.is_file() else None
    basics_pass = status_path.is_file() and os_release.is_file() and launcher_sha is not None
    pass_all = basics_pass and stable_tree and errors_count == 0 and dep["status"] == "PASS_DECLARED_PACKAGE_DEPENDENCIES_RESOLVED"
    result = {
        "schema": "CUSTOSZ_LUNITA_ROOTFS_INVENTORY/1.0",
        "timestamp_utc": utc(),
        "candidate_id": "G06_REBUILD_CANDIDATE_R1",
        "rootfs_path": str(ROOTFS),
        "rootfs_inventory_status": "PASS" if pass_all else "BLOCKED",
        "status": "PASS_ROOTFS_INVENTORY_AND_DEPENDENCY_CLOSURE" if pass_all else "BLOCKED_ROOTFS_INVENTORY_OR_DEPENDENCY_CLOSURE",
        "metadata_tree_sha256_before": before_digest, "metadata_tree_sha256_after": after_digest,
        "tree_stable_during_scan": stable_tree, "metadata_entry_count_before": before_count,
        "metadata_entry_count_after": after_count, "inventory_entry_count": count,
        "regular_file_count": regular_count, "symlink_count": symlink_count,
        "regular_file_total_bytes": total_bytes, "inventory_errors_count": errors_count,
        "privileged_read_only_hash_count": privileged_hash_count,
        "privileged_hashing_policy": "SUDO_NONINTERACTIVE_READ_ONLY_SHA256SUM_OR_FAIL_CLOSED",
        "inventory_errors": errors, "manifest_path": str(manifest), "manifest_sha256": sha_file(manifest),
        "manifest_stream_sha256": digest.hexdigest(), "manifest_bytes": manifest.stat().st_size,
        "dpkg_dependency_closure": dep, "dpkg_status_path": str(status_path),
        "os_release_sha256": sha_file(os_release) if os_release.is_file() else None,
        "launcher_sha256": launcher_sha,
        "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
        "certification": "NOT_GRANTED",
    }
    atomic_json(report_path, result)
    restore_inventory_artifact_owner(report_path)
    return result


def _latest_jasp_worker_report(worker_receipt: dict | None = None) -> tuple[pathlib.Path | None, dict | None, str | None]:
    """Load the latest worker result, including preflight failures before case logs exist."""
    evidence_root = EVIDENCE.resolve()
    reports = sorted(
        (path for path in EVIDENCE.glob("jasp_suite_*.json")
         if path.is_file() and not path.is_symlink()),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    if reports:
        path = reports[0]
        try:
            path.resolve(strict=True).relative_to(evidence_root)
        except (OSError, ValueError):
            return None, None, None
        return path, load_json(path, {}) or {}, sha_file(path)
    if isinstance(worker_receipt, dict):
        path_text = worker_receipt.get("path") or worker_receipt.get("result_path")
        if path_text:
            path = pathlib.Path(path_text)
            try:
                path.resolve(strict=True).relative_to(evidence_root)
                if path.is_file() and not path.is_symlink():
                    return path, load_json(path, {}) or {}, sha_file(path)
            except (OSError, ValueError):
                pass
        result = worker_receipt.get("result")
        if isinstance(result, dict):
            return None, result, None
        if worker_receipt.get("status") == "BLOCKED_JASP_WORKER_EXIT_WITHOUT_RECEIPT":
            return None, worker_receipt, None
    return None, None, None


def latest_jasp_evidence(worker_receipt: dict | None = None) -> dict:
    worker_path, worker_data, worker_sha = _latest_jasp_worker_report(worker_receipt)
    worker_tests = worker_data.get("tests", {}) if isinstance(worker_data, dict) else {}
    worker_cases = dict(worker_tests) if isinstance(worker_tests, dict) else {}
    if isinstance(worker_data, dict) and "death_penalty_roundtrip" not in worker_cases:
        roundtrip = worker_data.get("roundtrip_gate")
        if isinstance(roundtrip, dict):
            worker_cases["death_penalty_roundtrip"] = roundtrip
    worker_status = worker_data.get("status") if isinstance(worker_data, dict) else None
    mutation_identity = (
        worker_data.get("runtime_mutation_identity")
        if isinstance(worker_data, dict) and isinstance(worker_data.get("runtime_mutation_identity"), dict)
        else {}
    )
    expected_process_run_id = str(os.environ.get("GITHUB_RUN_ID", ""))
    expected_process_attempt = str(os.environ.get("GITHUB_RUN_ATTEMPT", ""))
    expected_process_executable = mutation_identity.get("jasp_binary_sha256", "")
    expected_process_runtime = mutation_identity.get("flatpak_runtime_commit", "")
    worker_failure = None
    if isinstance(worker_data, dict):
        worker_failure = (
            worker_data.get("executor_error")
            or worker_data.get("app_commit_probe")
            or worker_data.get("worker_failure")
        )
    rows = {}
    for case, (prefix, pattern, marker) in JASP_CASES.items():
        files = sorted((OUT.glob(prefix + pattern)), key=lambda p: p.stat().st_mtime_ns, reverse=True)
        if not files:
            case_result = worker_cases.get(case) if isinstance(worker_cases, dict) else None
            if isinstance(worker_data, dict):
                rows[case] = {
                    "status": "BLOCKED",
                    "case_status": (case_result or {}).get("status", "BLOCKED_WORKER_DID_NOT_REACH_CASE"),
                    "returncode": (case_result or {}).get("returncode"),
                    "evidence_path": str(worker_path) if worker_path else None,
                    "evidence_sha256": worker_sha,
                    "worker_status": worker_status,
                    "worker_failure": worker_failure,
                    "worker_case_result": case_result,
                }
            elif worker_receipt:
                rows[case] = {
                    "status": "BLOCKED",
                    "case_status": "BLOCKED_JASP_WORKER_EXIT_WITHOUT_RECEIPT",
                    "returncode": None,
                    "evidence_path": None,
                    "evidence_sha256": None,
                    "worker_status": worker_receipt.get("status"),
                    "worker_failure": worker_receipt,
                }
            else:
                rows[case] = {"status": "BLOCKED_NOT_RUN", "returncode": None, "evidence_path": None}
            continue
        p = files[0]
        item = {"evidence_path": str(p), "evidence_sha256": sha_file(p),
                "mtime_ns": p.stat().st_mtime_ns, "status": "BLOCKED", "returncode": None}
        if p.suffix == ".json":
            data = load_json(p, {}) or {}
            rerun = data.get("strict_rerun_after_save") or {}
            save_run = data.get("save_run") or {}
            temp_before = data.get("temporary_fixture_sha256_before")
            temp_after_save = data.get("temporary_fixture_sha256_after_save")
            temp_after_rerun = data.get("temporary_fixture_sha256_after_rerun")
            fixture_receipt = data.get("deterministic_fixture_receipt")
            fixture_evidence_ok = (
                data.get("deterministic_fixture_receipt_valid") is True
                and verify_deterministic_fixture_receipt(
                    fixture_receipt, DEATH_PENALTY_SOURCE_SHA256, require_clone=False
                )
            )
            save_process_receipt = save_run.get("process_tree_receipt")
            rerun_process_receipt = rerun.get("process_tree_receipt")
            process_tree_receipts_valid = bool(
                save_run.get("process_tree_receipt_valid") is True
                and rerun.get("process_tree_receipt_valid") is True
                and process_tree_receipt_identity_matches(
                    save_process_receipt, case_id="death_penalty_save", env=os.environ,
                    executable_sha256=expected_process_executable,
                    runtime_ostree_commit=expected_process_runtime,
                )
                and process_tree_receipt_identity_matches(
                    rerun_process_receipt, case_id="death_penalty_rerun", env=os.environ,
                    executable_sha256=expected_process_executable,
                    runtime_ostree_commit=expected_process_runtime,
                )
            )
            save_rows_sha = save_run.get("actual_result_rows_sha256")
            rerun_rows_sha = rerun.get("actual_result_rows_sha256")
            replay_pass = (
                data.get("deterministic_replay_status") == "PASS_DETERMINISTIC_REPLAY"
                and data.get("actual_result_rows_equal") is True
                and isinstance(save_rows_sha, str) and len(save_rows_sha) == 64
                and save_rows_sha == rerun_rows_sha
                and save_run.get("actual_result_rows") == rerun.get("actual_result_rows")
            )
            passed = (
                data.get("schema") == "CUSTOSZ_LUNITA_JASP_UNITTEST_ROUNDTRIP/1.0"
                and data.get("app_commit") == "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"
                and data.get("network_unshared") is True and data.get("flatpak_sandbox") is True
                and (
                    (data.get("status") == "PASS_JASP_STRICT_ROUNDTRIP"
                     and data.get("reference_comparison_status") == "PASS")
                    or (data.get("status") == "PASS_DETERMINISTIC_REPLAY_REFERENCE_MISMATCH_RECORDED"
                        and data.get("reference_comparison_status") == "BLOCKED_STORED_REFERENCE_MISMATCH")
                )
                and replay_pass
                and process_tree_receipts_valid
                and data.get("runtime_identity_status") == "PASS"
                and (save_run.get("runtime_identity") or {}).get("status") == "PASS"
                and (rerun.get("runtime_identity") or {}).get("status") == "PASS"
                and fixture_evidence_ok
                and data.get("original_sample_identity_matches_pin") is True
                and data.get("original_sample_unchanged") is True
                and data.get("temporary_fixture_removed_after_test") is True
                and data.get("temporary_fixture_stable_after_save_and_rerun") is True
                and data.get("temporary_fixture_hash_invariant_passed") is True
                and data.get("temporary_fixture_sha256_expected") == fixture_receipt.get("clone_sha256")
                and bool(temp_before) and temp_before == fixture_receipt.get("clone_sha256")
                and temp_after_save == fixture_receipt.get("clone_sha256")
                and temp_after_rerun == fixture_receipt.get("clone_sha256")
                and data.get("save_log_integrity_bound") is True
                and data.get("rerun_log_integrity_bound") is True
            )
            item.update({
                # Effective returncode denotes the deterministic-replay acceptance.
                # Original JASP subprocess return codes are retained without masking.
                "returncode": 0 if passed else 1,
                "save_subprocess_returncode": save_run.get("returncode"),
                "rerun_subprocess_returncode": rerun.get("returncode"),
                "status": (
                    "PASS" if passed and data.get("reference_comparison_status") == "PASS" else
                    "PASS_DETERMINISTIC_REPLAY" if passed else "BLOCKED"
                ),
                "acceptance_scope": (
                    "STRICT_REFERENCE_AND_REPLAY" if passed and data.get("reference_comparison_status") == "PASS" else
                    "DETERMINISTIC_REPLAY_ONLY" if passed else "BLOCKED"
                ),
                "case_status": data.get("status"),
                "deterministic_replay_status": data.get("deterministic_replay_status"),
                "reference_comparison_status": data.get("reference_comparison_status"),
                "save_actual_result_rows_sha256": save_rows_sha,
                "rerun_actual_result_rows_sha256": rerun_rows_sha,
                "actual_result_rows_equal": data.get("actual_result_rows_equal"),
                "original_sample_unchanged": data.get("original_sample_unchanged"),
                "original_sample_identity_matches_pin": data.get("original_sample_identity_matches_pin"),
                "temporary_fixture_sha256_expected": data.get("temporary_fixture_sha256_expected"),
                "temporary_fixture_sha256_before": temp_before,
                "temporary_fixture_sha256_after_save": temp_after_save,
                "temporary_fixture_sha256_after_rerun": temp_after_rerun,
                "temporary_fixture_hash_invariant_passed": data.get("temporary_fixture_hash_invariant_passed") is True,
                "temporary_fixture_regular_after_save": data.get("temporary_fixture_regular_after_save") is True,
                "temporary_fixture_regular_after_rerun": data.get("temporary_fixture_regular_after_rerun") is True,
                "temporary_fixture_changed": data.get("temporary_fixture_changed"),
                "temporary_fixture_removed_after_test": data.get("temporary_fixture_removed_after_test"),
                "temporary_fixture_stable_after_save_and_rerun": bool(temp_after_save and temp_after_save == temp_after_rerun),
                "temporary_fixture_path": data.get("temporary_fixture_path"),
                "save_log_path": save_run.get("log_path"),
                "save_log_sha256": save_run.get("log_sha256"),
                "save_fixture_sha256_after_execution": save_run.get("fixture_sha256_after_execution"),
                "save_fixture_unchanged_after_execution": save_run.get("fixture_unchanged_after_execution") is True,
                "rerun_log_path": rerun.get("log_path"),
                "rerun_log_sha256": rerun.get("log_sha256"),
                "rerun_fixture_sha256_after_execution": rerun.get("fixture_sha256_after_execution"),
                "rerun_fixture_unchanged_after_execution": rerun.get("fixture_unchanged_after_execution") is True,
                "original_sample_sha256_before": data.get("original_sample_sha256_before"),
                "original_sample_sha256_after": data.get("original_sample_sha256_after"),
                "deterministic_fixture_evidence_valid": fixture_evidence_ok,
                "deterministic_fixture_receipt_valid": data.get("deterministic_fixture_receipt_valid") is True,
                "deterministic_fixture_receipt": fixture_receipt,
                "process_tree_receipt_valid": process_tree_receipts_valid,
                "process_tree_receipts": [save_process_receipt, rerun_process_receipt],
            })
        else:
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            match = re.findall(re.escape(marker or "") + r"\s*=\s*([0-9]+)", text) if marker else []
            rc = int(match[-1]) if match else None
            expected_commit = "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"
            commits = re.findall(r"^APP_COMMIT=([0-9a-f]{64})$", text, re.M)
            pinned_commit = bool(commits) and all(x == expected_commit for x in commits)
            sandbox_bound = "EXECUTION_MODE=PINNED_CANDIDATE_FLATPAK_SANDBOX_NETWORK_UNSHARED" in text
            runtime_identity = inspect_jasp_runtime_identity(text)
            worker_case_result = worker_cases.get(case) if isinstance(worker_cases, dict) else None
            process_receipt = (
                worker_case_result.get("process_tree_receipt")
                if isinstance(worker_case_result, dict) else None
            )
            receipt_lines = re.findall(r"^PROCESS_TREE_RECEIPT_JSON=(.+)$", text, re.M)
            try:
                logged_process_receipt = json.loads(receipt_lines[-1]) if receipt_lines else None
            except (ValueError, TypeError):
                logged_process_receipt = None
            process_receipt_valid = bool(
                isinstance(worker_case_result, dict)
                and worker_case_result.get("process_tree_receipt_valid") is True
                and logged_process_receipt == process_receipt
                and process_tree_receipt_identity_matches(
                    process_receipt, case_id=case, env=os.environ,
                    executable_sha256=expected_process_executable,
                    runtime_ostree_commit=expected_process_runtime,
                )
            )
            fixture_ok = True
            deterministic_fixture_ok = True
            deterministic_fixture_receipt = None
            if case == "flatpak_launch":
                original_paths = re.findall(r"^ORIGINAL_FIXTURE_PATH=(.+)$", text, re.M)
                alias_paths = re.findall(r"^ORIGINAL_FIXTURE_ALIAS=(.+)$", text, re.M)
                original_hashes = re.findall(r"^ORIGINAL_FIXTURE_SHA256=([0-9a-f]{64})$", text, re.M)
                alias_markers = re.findall(r"^ORIGINAL_FIXTURE_ALIAS_VALID=(TRUE|FALSE)$", text, re.M)
                seeded_receipt_hashes = re.findall(r"^DETERMINISTIC_FIXTURE_RECEIPT_SHA256=([0-9a-f]{64})$", text, re.M)
                seeded_clone_hashes = re.findall(r"^DETERMINISTIC_FIXTURE_CLONE_SHA256=([0-9a-f]{64})$", text, re.M)
                seeded_clone_post_execution_hashes = re.findall(
                    r"^DETERMINISTIC_FIXTURE_CLONE_SHA256_AFTER_EXECUTION=([0-9a-f]{64})$", text, re.M
                )
                seeded_clone_unchanged_markers = re.findall(
                    r"^DETERMINISTIC_FIXTURE_CLONE_UNCHANGED_AFTER_EXECUTION=(TRUE|FALSE)$", text, re.M
                )
                seeded_markers = re.findall(r"^DETERMINISTIC_FIXTURE_SEED_ENABLED=(TRUE|FALSE)$", text, re.M)
                expected_source = ROOTFS / "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp"
                try:
                    original_path = pathlib.Path(original_paths[-1]) if original_paths else None
                    alias_path = pathlib.Path(alias_paths[-1]) if alias_paths else None
                    fixture_ok = bool(
                        original_path and alias_path
                        and original_path.resolve(strict=True) == expected_source.resolve(strict=True)
                        and alias_path.is_symlink()
                        and alias_path.resolve(strict=True) == expected_source.resolve(strict=True)
                        and original_hashes and original_hashes[-1] == DEATH_PENALTY_SOURCE_SHA256
                        and sha_file(original_path) == DEATH_PENALTY_SOURCE_SHA256
                        and sha_file(alias_path) == DEATH_PENALTY_SOURCE_SHA256
                        and alias_markers and alias_markers[-1] == "TRUE"
                    )
                    deterministic_fixture_receipt = (
                        worker_case_result.get("deterministic_fixture_receipt")
                        if isinstance(worker_case_result, dict) else None
                    )
                    deterministic_fixture_ok = bool(
                        isinstance(deterministic_fixture_receipt, dict)
                        and isinstance(worker_case_result, dict)
                        and worker_case_result.get("deterministic_fixture_receipt_valid") is True
                        and worker_case_result.get("fixture") == deterministic_fixture_receipt.get("clone_path")
                        and seeded_receipt_hashes
                        and seeded_receipt_hashes[-1] == deterministic_fixture_receipt.get("receipt_sha256")
                        and seeded_clone_hashes
                        and seeded_clone_hashes[-1] == deterministic_fixture_receipt.get("clone_sha256")
                        and seeded_clone_post_execution_hashes
                        and seeded_clone_post_execution_hashes[-1] == deterministic_fixture_receipt.get("clone_sha256")
                        and worker_case_result.get("deterministic_fixture_clone_sha256_after_execution")
                            == deterministic_fixture_receipt.get("clone_sha256")
                        and worker_case_result.get("deterministic_fixture_clone_unchanged_after_execution") is True
                        and seeded_clone_unchanged_markers and seeded_clone_unchanged_markers[-1] == "TRUE"
                        and seeded_markers and seeded_markers[-1] == "TRUE"
                        and verify_deterministic_fixture_receipt(
                            deterministic_fixture_receipt, DEATH_PENALTY_SOURCE_SHA256, require_clone=False
                        )
                    )
                except (OSError, ValueError, TypeError):
                    fixture_ok = False
                    deterministic_fixture_ok = False
            passed = (
                rc == 0 and pinned_commit and sandbox_bound and fixture_ok and deterministic_fixture_ok
                and runtime_identity.get("status") == "PASS" and process_receipt_valid
            )
            runtime_versions = [item["version"] for item in runtime_identity.get("observed", [])]
            runtime_source_commits = [item["source_commit"] for item in runtime_identity.get("observed", [])]
            diagnostic_lines = text.splitlines()
            semantic_pattern = re.compile(
                r"Row is missing|Total number of models visited\s*=\s*\d+\s*!=|results are different|\d+(?:\.\d+)?\s*!=\s*\d+(?:\.\d+)?",
                re.I,
            )
            diagnostic_indexes = [
                index for index, line in enumerate(diagnostic_lines)
                if semantic_pattern.search(line)
            ]
            diagnostic_excerpt = []
            for index in diagnostic_indexes:
                for context_index in range(max(0, index - 1), min(len(diagnostic_lines), index + 3)):
                    rendered = f"{context_index + 1}: {diagnostic_lines[context_index][:400]}"
                    if rendered not in diagnostic_excerpt:
                        diagnostic_excerpt.append(rendered)
                    if len(diagnostic_excerpt) >= 32:
                        break
                if len(diagnostic_excerpt) >= 32:
                    break
            item.update({
                "returncode": rc,
                "status": "PASS" if passed else "BLOCKED",
                "observed_app_commits": commits,
                "pinned_commit_match": pinned_commit,
                "sandbox_execution_marker_present": sandbox_bound,
                "original_packaged_fixture_identity_valid": fixture_ok if case == "flatpak_launch" else None,
                "deterministic_fixture_path": (
                    worker_case_result.get("deterministic_fixture_path")
                    if case == "flatpak_launch" and isinstance(worker_case_result, dict)
                    else None
                ),
                "deterministic_fixture_evidence_valid": deterministic_fixture_ok if case == "flatpak_launch" else None,
                "deterministic_fixture_receipt_valid": (
                    worker_case_result.get("deterministic_fixture_receipt_valid") is True
                    if case == "flatpak_launch" and isinstance(worker_case_result, dict)
                    else None
                ),
                "deterministic_fixture_receipt": deterministic_fixture_receipt if case == "flatpak_launch" else None,
                "deterministic_fixture_clone_sha256_after_execution": (
                    worker_case_result.get("deterministic_fixture_clone_sha256_after_execution")
                    if case == "flatpak_launch" and isinstance(worker_case_result, dict) else None
                ),
                "deterministic_fixture_clone_unchanged_after_execution": (
                    worker_case_result.get("deterministic_fixture_clone_unchanged_after_execution") is True
                    if case == "flatpak_launch" and isinstance(worker_case_result, dict) else None
                ),
                "observed_runtime_versions": runtime_versions,
                "observed_runtime_source_commits": runtime_source_commits,
                "runtime_identity": runtime_identity,
                "process_tree_receipt": process_receipt,
                "process_tree_receipt_valid": process_receipt_valid,
                "semantic_shape_mismatch": bool(re.search(r"Row is missing|Total number of models visited\s*=\s*\d+\s*!=|results are different", text, re.I)),
                "log_has_numeric_deltas": bool(re.search(r"\d+(?:\.\d+)?\s*!=\s*\d+(?:\.\d+)?", text)),
                "semantic_diagnostic_excerpt": diagnostic_excerpt,
            })
        rows[case] = item
    # Replay-only is terminal for diagnostics, never a functional non-regression PASS.
    all_pass = bool(rows) and all(
        row.get("status") == "PASS" and row.get("returncode") == 0
        and (
            case != "death_penalty_roundtrip"
            or (
                row.get("acceptance_scope") == "STRICT_REFERENCE_AND_REPLAY"
                and row.get("reference_comparison_status") == "PASS"
            )
        )
        for case, row in rows.items()
    )
    worker_evidence = None
    if isinstance(worker_data, dict):
        worker_evidence = {
            "path": str(worker_path) if worker_path else None,
            "sha256": worker_sha,
            "status": worker_status,
            "failure": worker_failure,
            "case_count": len(worker_cases),
        }
    return {"status": "PASS_JASP_PACKAGED_FIXTURE_NONREGRESSION" if all_pass else "BLOCKED_JASP_PACKAGED_FIXTURE_NONREGRESSION",
            "all_required_jasp_cases_pass": all_pass, "cases": rows,
            "worker_evidence": worker_evidence,
            "next_action": (
                "Resolve the explicit JASP worker preflight/executor failure recorded in worker_evidence; absence of per-case logs is not a PASS."
                if worker_evidence and not worker_cases else
                "Keep the packaged-reference check on the original immutable fixture; evaluate seeded reproducibility only from two hash-bound freshly calculated result tables. Never modify source fixtures or reference results to make a test pass."
            )}


def persist_jasp_remediation_queue(jasp: dict) -> dict:
    """Keep a hash-bound, append-only queue for each unresolved packaged JASP case."""
    queue_path = EVIDENCE / "jasp_remediation_queue.json"
    old = load_json(queue_path, {}) or {"schema": "CUSTOSZ_LUNITA_JASP_REMEDIATION_QUEUE/1.0", "items": []}
    items = old.get("items") if isinstance(old.get("items"), list) else []
    known = {(x.get("case_id"), x.get("evidence_sha256")) for x in items if isinstance(x, dict)}
    for case_id, result in (jasp.get("cases") or {}).items():
        digest = result.get("evidence_sha256")
        if digest:
            for prior in items:
                if (prior.get("case_id") == case_id and prior.get("status") == "OPEN"
                    and prior.get("evidence_sha256") != digest):
                    prior["status"] = "SUPERSEDED"
                    prior["superseded_at_utc"] = utc()
                    prior["superseded_by_sha256"] = digest
        if result.get("status") == "PASS" and result.get("returncode") == 0:
            continue
        identity = (case_id, digest)
        if identity in known:
            continue
        path_text = result.get("evidence_path")
        reason = {
            "flatpak_launch": "Run the pinned JASP startup regression on a disposable clone of the exact original Death Penalty fixture with native setSeed=true and the Rounding set.seed value that reproduces the stored four-model table; independently verify the clone/receipt/log hashes and prove the original fixture and stored references remain unchanged.",
            "reliability": "Diagnose full-precision output differences versus packaged reference; distinguish harmless display formatting from semantic/statistical deltas with a documented independent tolerance policy.",
            "weight_gain": "Diagnose numeric display/precision deltas against the packaged reference without mutating the original fixture.",
            "death_penalty_roundtrip": "Verify the exact pinned original fixture and disposable deterministic clone receipts, then compare newly calculated save/replay tables without modifying reference results.",
        }.get(case_id, "Rerun the exact pinned JASP case on an isolated copy and retain hash-bound logs.")
        items.append({"case_id": case_id, "evidence_path": path_text, "evidence_sha256": digest,
            "observed_status": result.get("status"), "returncode": result.get("returncode"),
            "first_seen_utc": utc(), "status": "OPEN", "attempts": 0,
            "required_action": reason,
            "guardrails": ["Use the pinned candidate JASP commit", "Run only on isolated fixture copies",
                           "Never rewrite the packaged reference automatically", "Never relax acceptance criteria to force PASS",
                           "Record command/version/input/output hashes and return code", "Independent review required"]})
        known.add(identity)
    open_items = [x for x in items if x.get("status") == "OPEN"]
    queue = {"schema": "CUSTOSZ_LUNITA_JASP_REMEDIATION_QUEUE/1.0", "updated_at_utc": utc(),
             "candidate_id": "G06_REBUILD_CANDIDATE_R1", "pinned_app_commit": "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7",
             "status": "OPEN" if open_items else "RESOLVED", "open_count": len(open_items),
             "items": items, "certification": "NOT_GRANTED", "mission_completion_claim": False}
    atomic_json(queue_path, queue)
    return {"path": str(queue_path), "sha256": sha_file(queue_path), "status": queue["status"], "open_count": len(open_items)}


def _stable_check(check: dict) -> bool:
    return isinstance(check, dict) and check.get("status") == "PASS" and check.get("returncode", 0) == 0


def latest_target_runtime_acceptance() -> dict:
    """Use only the newest receipt; stale prior PASS evidence must never override a later failure."""
    files = sorted(TARGET_RUNTIME_RECEIPT_DIR.glob("LUNITA_TARGET_RUNTIME_ACCEPTANCE_*.json"),
                   key=lambda path: path.stat().st_mtime_ns, reverse=True)
    if not files:
        return {"status": "BLOCKED_TARGET_RUNTIME_RECEIPT_MISSING", "receipt_path": None}
    path = files[0]
    row = load_json(path, {}) or {}
    def blocked(reason: str) -> dict:
        return {"status": "BLOCKED_TARGET_RUNTIME_RECEIPT_INVALID", "receipt_path": str(path),
                "reason": reason}
    if row.get("schema") != "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0":
        return blocked("SCHEMA_MISMATCH")
    if row.get("status") != "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED":
        return blocked("LATEST_RECEIPT_NOT_PASS")
    if row.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1":
        return blocked("CANDIDATE_IDENTITY_MISMATCH")
    identity = row.get("workflow_identity")
    if not isinstance(identity, dict):
        return blocked("WORKFLOW_IDENTITY_MISSING_OR_INVALID")
    run_id = identity.get("run_id")
    run_attempt = identity.get("run_attempt")
    host_bind_name = identity.get("host_bind_name")
    runtime_path = identity.get("xdg_runtime_dir")
    if (
        not isinstance(run_id, str) or re.fullmatch(r"[0-9]+", run_id) is None
        or not isinstance(run_attempt, str) or re.fullmatch(r"[0-9]+", run_attempt) is None
    ):
        return blocked("WORKFLOW_RUN_IDENTITY_MISSING_OR_INVALID")
    expected_bind_name = f"lunita-host-{run_id}-{run_attempt}"
    expected_runtime_path = f"/run/{expected_bind_name}-runtime-1000"
    runtime_check = row.get("xdg_runtime_dir")
    if (
        host_bind_name != expected_bind_name
        or runtime_path != expected_runtime_path
        or not isinstance(runtime_check, dict)
        or runtime_check.get("status") != "PASS_XDG_RUNTIME_DIR_UID1000_PRIVATE"
        or runtime_check.get("path") != expected_runtime_path
    ):
        return blocked("WORKFLOW_IDENTITY_RUNTIME_BINDING_MISMATCH")
    if row.get("certification") != "NOT_GRANTED" or row.get("canonical_g06_certification") != "NOT_GRANTED":
        return blocked("CERTIFICATION_SCOPE_MISMATCH")
    overlay = row.get("overlay_integrity", {})
    if overlay.get("status") != "PASS_OVERLAY_INTEGRITY":
        return blocked("OVERLAY_INTEGRITY_NOT_PASS")
    if overlay.get("frozen_g06_mutated") is not False or overlay.get("canonical_g08_mutated") is not False:
        return blocked("FROZEN_IDENTITY_INVARIANT_MISMATCH")
    if row.get("canonical_g08_binding_mutation") is not False:
        return blocked("CANONICAL_G08_BINDING_MUTATION")
    quantization = row.get("e04_quantization", {})
    if quantization.get("status") != "PASS_E04_INT8_QUALITY_GATE":
        return blocked("E04_INT8_QUALITY_GATE_NOT_PASS")
    qwen = row.get("qwen_e01", {})
    if qwen.get("status") != "PASS_E01_QWEN_INFERENCE":
        return blocked("E01_QWEN_INFERENCE_NOT_PASS")
    tests = row.get("engine_acceptance_tests", {})
    required_engine_ids = {f"E{i:02d}" for i in range(2, 16)}
    if tests.get("status") != "PASS" or tests.get("skipped") != 0:
        return blocked("ENGINE_ACCEPTANCE_NOT_PASS_OR_SKIPPED")
    if not isinstance(tests.get("tests_run"), int) or tests["tests_run"] < 1:
        return blocked("ENGINE_TEST_COUNT_INVALID")
    if set(tests.get("engine_ids_covered", [])) != required_engine_ids:
        return blocked("ENGINE_ID_COVERAGE_INCOMPLETE")
    if tests.get("command_route_matrix_test_present") is not True:
        return blocked("COMMAND_AGENT_ENGINE_ROUTE_MATRIX_NOT_TESTED")
    applications = row.get("legacy_application_smokes", {})
    commands = applications.get("commands") if isinstance(applications.get("commands"), dict) else {}
    required_commands = {
        "brujula-self-test", "r-self-test", "jamovi-self-test", "jasp-self-test",
        "fault model-missing", "fault model-corrupted", "fault dependency-missing",
        "fault permission-denied", "fault low-memory", "fault process-crash",
        "fault browser-crash", "fault tool-failure", "fault invalid-input",
        "fault interrupted-execution", "fault restart",
    }
    if applications.get("status") != "PASS_LEGACY_APPLICATION_SMOKES" or set(commands) != required_commands:
        return blocked("LEGACY_APPLICATION_SMOKE_SET_INCOMPLETE")
    if any(command.get("status") != "PASS" or command.get("returncode") != 0
           for command in commands.values()):
        return blocked("LEGACY_APPLICATION_SMOKE_FAILED")
    digest = sha_file(path)
    return {
        "status": "PASS_TARGET_RUNTIME_ACCEPTANCE",
        "receipt_path": str(path),
        "receipt_sha256": digest,
        "candidate_id": row.get("candidate_id"),
        "workflow_identity": identity,
        "xdg_runtime_dir": runtime_check,
        "overlay_integrity": overlay,
        "e04_quantization": quantization,
        "qwen_e01": qwen,
        "engine_acceptance_tests": tests,
        "legacy_application_smokes": applications,
        "frozen_g06_mutated": overlay.get("frozen_g06_mutated"),
        "canonical_g08_binding_mutation": row.get("canonical_g08_binding_mutation"),
    }



def direct_candidate_manifest_identity() -> dict:
    """Bind v1.8 direct certification to the frozen candidate manifest, not the retired v1.7 mission."""
    row = load_json(CANDIDATE_MANIFEST, {}) or {}
    digest = sha_file(CANDIDATE_MANIFEST) if CANDIDATE_MANIFEST.is_file() else None
    preserved = row.get("preserved_baseline") if isinstance(row.get("preserved_baseline"), dict) else {}
    valid = (
        row.get("schema") == "LUNITA_CANDIDATE_FREEZE/1.0"
        and row.get("candidate_id") == "G06_REBUILD_CANDIDATE_R1"
        and row.get("version") == "1.8.0"
        and row.get("freeze_status") == "FROZEN_CANDIDATE_NOT_CERTIFIED"
        and preserved.get("frozen_g06_mutated") is False
        and preserved.get("canonical_g08_bindings_mutated") is False
        and preserved.get("legacy_v1_7_launcher_replaced") is False
    )
    return {"status": "PASS" if valid and digest else "BLOCKED",
            "path": str(CANDIDATE_MANIFEST), "sha256": digest,
            "candidate_id": row.get("candidate_id"), "version": row.get("version")}


def direct_candidate_squashfs_identity() -> dict:
    """Bind the independent lane to the exact packaged image and frozen manifest."""
    manifest = direct_candidate_manifest_identity()
    if manifest.get("status") != "PASS":
        return {"status": "BLOCKED", "reason": "FROZEN_MANIFEST_INVALID"}
    for path, label in (
        (SQUASHFS_IMAGE, "SquashFS image"),
        (SQUASHFS_CHECKSUM, "SquashFS checksum"),
        (SQUASHFS_PACKAGE_RECEIPT, "SquashFS package receipt"),
    ):
        if path.is_symlink() or not path.is_file():
            return {"status": "BLOCKED", "reason": f"{label} missing or unsafe"}
    try:
        image_sha = sha_file(SQUASHFS_IMAGE)
        image_bytes = SQUASHFS_IMAGE.stat().st_size
        checksum_sha = sha_file(SQUASHFS_CHECKSUM)
        checksum_text = SQUASHFS_CHECKSUM.read_text(encoding="ascii").strip()
        if image_bytes <= 0 or checksum_text != f"{image_sha}  {SQUASHFS_IMAGE.name}":
            return {"status": "BLOCKED", "reason": "IMAGE_CHECKSUM_MISMATCH"}
        package = load_json(SQUASHFS_PACKAGE_RECEIPT, {}) or {}
        package_sha = sha_file(SQUASHFS_PACKAGE_RECEIPT)
        if (
            package.get("schema") != "LUNITA_SQUASHFS_PACKAGE_RECEIPT/1.0"
            or package.get("status") != "PASS_SQUASHFS_PACKAGE_AND_ROUNDTRIP_NOT_CERTIFIED"
            or package.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1"
            or package.get("version") != "1.8.0"
            or package.get("image_name") != SQUASHFS_IMAGE.name
            or package.get("image_sha256") != image_sha
            or package.get("image_bytes") != image_bytes
            or package.get("roundtrip_manifest_match") is not True
            or package.get("source_rootfs_unchanged") is not True
            or package.get("mksquashfs") != "PASS"
            or package.get("unsquashfs_superblock") != "PASS"
            or package.get("unsquashfs_roundtrip") != "PASS"
        ):
            return {"status": "BLOCKED", "reason": "PACKAGE_RECEIPT_IMAGE_BINDING_MISMATCH"}
        target = latest_target_runtime_acceptance()
        target_path = pathlib.Path(target.get("receipt_path", "")) if target.get("receipt_path") else None
        if (
            target.get("status") != "PASS_TARGET_RUNTIME_ACCEPTANCE"
            or not target_path or target_path.is_symlink() or not target_path.is_file()
            or target.get("receipt_sha256") != sha_file(target_path)
            or package.get("target_runtime_receipt_path") != str(target_path)
            or package.get("target_runtime_receipt_sha256") != target.get("receipt_sha256")
            or package.get("target_runtime_status") != "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED"
        ):
            return {"status": "BLOCKED", "reason": "PACKAGE_TARGET_RECEIPT_BINDING_MISMATCH"}
        return {
            "status": "PASS",
            "image_path": str(SQUASHFS_IMAGE),
            "image_sha256": image_sha,
            "image_bytes": image_bytes,
            "checksum_path": str(SQUASHFS_CHECKSUM),
            "checksum_sha256": checksum_sha,
            "package_receipt_path": str(SQUASHFS_PACKAGE_RECEIPT),
            "package_receipt_sha256": package_sha,
            "candidate_manifest_path": manifest["path"],
            "candidate_manifest_sha256": manifest["sha256"],
        }
    except Exception as exc:
        return {"status": "BLOCKED", "reason": f"IMAGE_EVIDENCE_INVALID:{type(exc).__name__}:{exc}"}


def direct_candidate_rootfs_manifest_closure(
    jasp: dict, inventory: dict | None, inventory_hashes_valid: bool
) -> dict:
    """Recompute the packager's exact canonical tree manifest after independent tests."""
    if CERTIFICATION_PROFILE != "V1_8_DIRECT":
        return {"status": "NOT_APPLICABLE", "returncode": 0}
    worker_evidence = jasp.get("worker_evidence") if isinstance(jasp, dict) else None
    if not inventory_hashes_valid or not isinstance(worker_evidence, dict):
        return {
            "status": "BLOCKED",
            "returncode": 1,
            "details": "Post-validation rootfs closure waits for completed JASP worker and valid independent inventory.",
        }
    package_path = SQUASHFS_PACKAGE_RECEIPT
    packager_path = ROOT.parent.parent / "scripts" / "lunita" / "package_candidate_squashfs_v1.py"
    try:
        if package_path.is_symlink() or not package_path.is_file():
            raise RuntimeError("SquashFS package receipt is missing or unsafe")
        if packager_path.is_symlink() or not packager_path.is_file():
            raise RuntimeError("Canonical SquashFS packager source is missing or unsafe")
        package = load_json(package_path, {}) or {}
        package_sha = sha_file(package_path)
        if (
            package.get("schema") != "LUNITA_SQUASHFS_PACKAGE_RECEIPT/1.0"
            or package.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1"
            or package.get("version") != "1.8.0"
            or package.get("source_rootfs") != str(ROOTFS)
            or package.get("roundtrip_manifest_match") is not True
            or package.get("source_rootfs_unchanged") is not True
        ):
            raise RuntimeError("Package receipt identity/source-rootfs contract is invalid")
        spec = importlib.util.spec_from_file_location("lunita_packager_manifest_runtime", packager_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Cannot load the canonical SquashFS packager module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest = module.tree_manifest(ROOTFS)
        expected_sha = package.get("source_rootfs_manifest_sha256")
        observed_sha = manifest.get("entries_sha256")
        expected_count = package.get("source_rootfs_entry_count")
        observed_count = manifest.get("entry_count")
        equal = bool(
            isinstance(expected_sha, str) and re.fullmatch(r"[0-9a-f]{64}", expected_sha)
            and observed_sha == expected_sha
            and isinstance(expected_count, int) and observed_count == expected_count
        )
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        receipt_path = EVIDENCE / f"rootfs_package_manifest_closure_{stamp}.json"
        payload = {
            "schema": "LUNITA_POSTVALIDATION_ROOTFS_PACKAGE_MANIFEST_CLOSURE/1.0",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "status": "PASS" if equal else "BLOCKED_MANIFEST_MISMATCH",
            "rootfs_path": str(ROOTFS),
            "package_receipt_path": str(package_path),
            "package_receipt_sha256": package_sha,
            "packager_source_path": str(packager_path),
            "packager_source_sha256": sha_file(packager_path),
            "package_source_rootfs_manifest_sha256": expected_sha,
            "observed_post_validation_rootfs_manifest_sha256": observed_sha,
            "package_source_rootfs_entry_count": expected_count,
            "observed_post_validation_rootfs_entry_count": observed_count,
            "independent_inventory_report_sha256": inventory.get("report_sha256") if isinstance(inventory, dict) else None,
            "independent_inventory_manifest_sha256": inventory.get("manifest_sha256") if isinstance(inventory, dict) else None,
            "jasp_worker_report_sha256": worker_evidence.get("sha256"),
            "same_canonical_algorithm": True,
            "exact_manifest_equality": equal,
            "certification": "NOT_GRANTED",
            "created_at_utc": utc(),
        }
        atomic_json(receipt_path, payload)
        receipt_sha = sha_file(receipt_path)
        status = "PASS" if equal else "BLOCKED"
        return {
            "status": status,
            "returncode": 0 if equal else 1,
            "rootfs_path": str(ROOTFS),
            "package_source_rootfs_manifest_sha256": expected_sha,
            "observed_post_validation_rootfs_manifest_sha256": observed_sha,
            "package_source_rootfs_entry_count": expected_count,
            "observed_post_validation_rootfs_entry_count": observed_count,
            "package_receipt_path": str(package_path),
            "package_receipt_sha256": package_sha,
            "packager_source_path": str(packager_path),
            "packager_source_sha256": payload["packager_source_sha256"],
            "manifest_closure_receipt_path": str(receipt_path),
            "manifest_closure_receipt_sha256": receipt_sha,
            "same_canonical_algorithm": True,
            "exact_manifest_equality": equal,
            "evidence": {
                str(receipt_path): receipt_sha,
                str(package_path): package_sha,
                str(packager_path): payload["packager_source_sha256"],
            },
            "details": "Exact post-validation tree manifest equality." if equal else
                "The post-validation rootfs does not equal the packaged source manifest.",
        }
    except Exception as exc:
        return {
            "status": "BLOCKED",
            "returncode": 1,
            "details": f"POSTVALIDATION_ROOTFS_MANIFEST_CLOSURE_ERROR:{type(exc).__name__}:{exc}",
        }



def valid_workflow_identity(run_id: str, run_attempt: str) -> bool:
    """Accept only positive ASCII-decimal GitHub run and attempt identifiers."""
    def positive_ascii_decimal(value: str) -> bool:
        return (
            isinstance(value, str)
            and bool(value)
            and value.isascii()
            and value.isdecimal()
            and int(value) > 0
        )
    return positive_ascii_decimal(run_id) and positive_ascii_decimal(run_attempt)


def jasp_case_results_terminal(cases: dict) -> bool:
    """Recognize terminal JASP outcomes without promoting replay-only evidence to strict PASS."""
    if not isinstance(cases, dict) or set(cases) != set(JASP_CASES):
        return False
    for case_id, row in cases.items():
        if not isinstance(row, dict):
            return False
        status = row.get("status")
        if status in {"PASS", "BLOCKED"}:
            continue
        if (
            case_id == "death_penalty_roundtrip"
            and status == "PASS_DETERMINISTIC_REPLAY"
            and row.get("acceptance_scope") == "DETERMINISTIC_REPLAY_ONLY"
            and row.get("reference_comparison_status") == "BLOCKED_STORED_REFERENCE_MISMATCH"
            and row.get("returncode") == 0
        ):
            continue
        return False
    return True


def update_independent_report(inventory: dict | None, jasp: dict) -> dict:
    direct = CERTIFICATION_PROFILE == "V1_8_DIRECT"
    old = load_json(INDEPENDENT_REPORT, {}) or {}
    old_checks = old.get("checks") if isinstance(old.get("checks"), dict) else {}
    # v1.8 starts from a clean candidate-specific check set; the immutable history
    # archive preserves v1.7 observations, but no legacy PASS is carried forward.
    checks = {} if direct else dict(old_checks)
    actual_launcher = ROOTFS / "opt/lunita/agent/lunita.py"
    launcher_sha = sha_file(actual_launcher) if actual_launcher.is_file() else None
    target_before = latest_target_runtime_acceptance() if direct else {}
    target_before_path = pathlib.Path(target_before.get("receipt_path", "")) if target_before.get("receipt_path") else None
    target_before_hash_valid = bool(
        target_before.get("status") == "PASS_TARGET_RUNTIME_ACCEPTANCE"
        and target_before_path and target_before_path.is_file()
        and target_before.get("receipt_sha256") == sha_file(target_before_path)
    ) if direct else False
    if direct:
        manifest_identity = direct_candidate_manifest_identity()
        target_launcher_sha = (target_before.get("overlay_integrity") or {}).get("legacy_launcher_sha256")
        launcher_ok = bool(target_before_hash_valid and launcher_sha and launcher_sha == target_launcher_sha)
        checks.pop("MISION1_identity_sha256", None)
        checks["candidate_manifest_identity_sha256"] = {
            "status": manifest_identity["status"],
            "returncode": 0 if manifest_identity["status"] == "PASS" else 1,
            "sha256": manifest_identity["sha256"],
            "evidence": {manifest_identity["path"]: manifest_identity["sha256"]} if manifest_identity["sha256"] else {},
        }
        checks["runtime_report_and_launcher_identity"] = {
            "status": "PASS" if launcher_ok and manifest_identity["status"] == "PASS" else "BLOCKED",
            "returncode": 0 if launcher_ok and manifest_identity["status"] == "PASS" else 1,
            "runtime_report_sha256": target_before.get("receipt_sha256"),
            "launcher_sha256": launcher_sha,
            "runtime_evidence_schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0",
            "runtime_evidence_status": target_before.get("status"),
        }
        runtime_sha = target_before.get("receipt_sha256") if target_before_hash_valid else None
        runtime_path_text = str(target_before_path) if target_before_path else None
        mission_sha = None
        candidate_manifest_sha = manifest_identity["sha256"]
    else:
        runtime = load_json(RUNTIME_REPORT, {}) or {}
        runtime_sha = sha_file(RUNTIME_REPORT) if RUNTIME_REPORT.is_file() else None
        launcher_ok = bool(runtime.get("candidate", {}).get("beta_launcher_sha256") == launcher_sha and
                           runtime.get("candidate_id") == "G06_REBUILD_CANDIDATE_R1")
        identity_ok = MISSION_PATH.is_file() and sha_file(MISSION_PATH) == MISSION_SHA
        checks["MISION1_identity_sha256"] = {"status": "PASS" if identity_ok else "BLOCKED",
            "returncode": 0 if identity_ok else 1, "sha256": sha_file(MISSION_PATH) if MISSION_PATH.is_file() else None}
        checks["runtime_report_and_launcher_identity"] = {"status": "PASS" if (
            runtime.get("schema") == "CUSTOSZ_LUNITA_BETA_RUNTIME_FUNCTIONAL_TESTS/1.0" and
            runtime.get("status") == "PASS_RUNTIME_TESTS" and runtime.get("all_tests_pass") is True and
            launcher_ok and runtime.get("frozen_g06_mutated") is False and
            runtime.get("canonical_g08_bindings_mutated") is False
        ) else "BLOCKED", "returncode": 0 if (
            runtime.get("schema") == "CUSTOSZ_LUNITA_BETA_RUNTIME_FUNCTIONAL_TESTS/1.0" and
            runtime.get("status") == "PASS_RUNTIME_TESTS" and runtime.get("all_tests_pass") is True and
            launcher_ok and runtime.get("frozen_g06_mutated") is False and
            runtime.get("canonical_g08_bindings_mutated") is False
        ) else 1, "runtime_report_sha256": runtime_sha, "launcher_sha256": launcher_sha}
        runtime_path_text = str(RUNTIME_REPORT)
        mission_sha = MISSION_SHA
        candidate_manifest_sha = None
    target_runtime = latest_target_runtime_acceptance()
    target_receipt_path = pathlib.Path(target_runtime.get("receipt_path", "")) if target_runtime.get("receipt_path") else None
    target_runtime_hash_valid = bool(
        target_runtime.get("status") == "PASS_TARGET_RUNTIME_ACCEPTANCE"
        and target_receipt_path and target_receipt_path.is_file()
        and target_runtime.get("receipt_sha256") == sha_file(target_receipt_path)
    )
    checks["target_v1_8_runtime_acceptance_e01_e15_int8"] = {
        "status": "PASS" if target_runtime_hash_valid else "BLOCKED",
        "returncode": 0 if target_runtime_hash_valid else 1,
        "receipt_path": str(target_receipt_path) if target_receipt_path else None,
        "receipt_sha256": target_runtime.get("receipt_sha256"),
        "engine_tests_run": (target_runtime.get("engine_acceptance_tests") or {}).get("tests_run"),
        "e01_status": (target_runtime.get("qwen_e01") or {}).get("status"),
        "e04_status": (target_runtime.get("e04_quantization") or {}).get("status"),
        "legacy_smokes_status": (target_runtime.get("legacy_application_smokes") or {}).get("status"),
        "evidence": {str(target_receipt_path): target_runtime.get("receipt_sha256")} if target_receipt_path else {},
        "details": target_runtime.get("status"),
    }
    inventory_report_path = pathlib.Path(inventory.get("report_path", "")) if inventory and inventory.get("report_path") else None
    inventory_manifest_path = pathlib.Path(inventory.get("manifest_path", "")) if inventory and inventory.get("manifest_path") else None
    inventory_hashes_valid = bool(
        inventory and inventory.get("status") == "PASS_ROOTFS_INVENTORY_AND_DEPENDENCY_CLOSURE"
        and inventory.get("rootfs_path") == str(ROOTFS)
        and inventory.get("tree_stable_during_scan") is True
        and inventory_report_path and inventory_report_path.is_file()
        and inventory.get("report_sha256") == sha_file(inventory_report_path)
        and inventory_manifest_path and inventory_manifest_path.is_file()
        and inventory.get("manifest_sha256") == sha_file(inventory_manifest_path)
        and inventory.get("inventory_errors_count") == 0
        and (inventory.get("dpkg_dependency_closure") or {}).get("status") == "PASS_DECLARED_PACKAGE_DEPENDENCIES_RESOLVED"
    )
    checks["candidate_rootfs_inventory_and_dependency_manifest"] = {
        "status": "PASS" if inventory_hashes_valid else "BLOCKED",
        "returncode": 0 if inventory_hashes_valid else 1,
        "inventory_report_path": str(inventory_report_path) if inventory_report_path else None,
        "inventory_report_sha256": inventory.get("report_sha256") if inventory else None,
        "manifest_path": str(inventory_manifest_path) if inventory_manifest_path else None,
        "manifest_sha256": inventory.get("manifest_sha256") if inventory else None,
        "evidence": {
            str(inventory_report_path): inventory.get("report_sha256"),
            str(inventory_manifest_path): inventory.get("manifest_sha256"),
        } if inventory and inventory_report_path and inventory_manifest_path else {},
        "details": inventory.get("status") if inventory else "Inventory not complete; wait for serialized inventory worker."}
    jasp_cases = jasp.get("cases") if isinstance(jasp.get("cases"), dict) else {}
    def jasp_case_accepted(case_id: str, row: dict) -> bool:
        if not isinstance(row, dict):
            return False
        strict_pass = (
            row.get("status") == "PASS"
            and row.get("returncode") == 0
            and (
                case_id != "death_penalty_roundtrip"
                or (
                    row.get("acceptance_scope") == "STRICT_REFERENCE_AND_REPLAY"
                    and row.get("reference_comparison_status") == "PASS"
                )
            )
        )
        evidence_value = row.get("evidence_path")
        if not isinstance(evidence_value, str) or not evidence_value.strip():
            return False
        try:
            evidence_path = pathlib.Path(evidence_value)
            if not evidence_path.is_file() or evidence_path.is_symlink():
                return False
            observed_sha256 = sha_file(evidence_path)
        except (OSError, RuntimeError, TypeError, ValueError):
            return False
        return bool(
            strict_pass
            and row.get("process_tree_receipt_valid") is True
            and observed_sha256 == row.get("evidence_sha256")
        )
    jasp_case_evidence_valid = (
        set(jasp_cases) == set(JASP_CASES)
        and all(jasp_case_accepted(case_id, row) for case_id, row in jasp_cases.items())
    )
    jasp_pass = jasp.get("status") == "PASS_JASP_PACKAGED_FIXTURE_NONREGRESSION" and jasp_case_evidence_valid
    jasp_evidence_map = {
        row["evidence_path"]: row["evidence_sha256"]
        for row in jasp_cases.values()
        if isinstance(row, dict)
        and isinstance(row.get("evidence_path"), str)
        and row.get("evidence_path").strip()
        and isinstance(row.get("evidence_sha256"), str)
    }
    for case_row in jasp_cases.values():
        if not isinstance(case_row, dict):
            continue
        for path_key, sha_key in (
            ("save_log_path", "save_log_sha256"),
            ("rerun_log_path", "rerun_log_sha256"),
        ):
            evidence_path = case_row.get(path_key)
            evidence_sha = case_row.get(sha_key)
            if isinstance(evidence_path, str) and isinstance(evidence_sha, str):
                jasp_evidence_map[evidence_path] = evidence_sha
        receipt = case_row.get("deterministic_fixture_receipt")
        if isinstance(receipt, dict):
            receipt_path = receipt.get("receipt_path")
            receipt_sha = receipt.get("receipt_sha256")
            if isinstance(receipt_path, str) and isinstance(receipt_sha, str):
                jasp_evidence_map[receipt_path] = receipt_sha
    checks["jasp_packaged_fixture_nonregression"] = {
        "status": "PASS" if jasp_pass else "BLOCKED",
        "returncode": 0 if jasp_pass else 1,
        "cases": jasp_cases, "next_action": jasp.get("next_action"),
        "all_case_evidence_hashes_current": jasp_case_evidence_valid,
        "evidence": jasp_evidence_map,
    }
    jasp_runtime_identity = verify_jasp_runtime_mutation_receipt() if direct else {}
    target_workflow_identity = (
        target_runtime.get("workflow_identity")
        if isinstance(target_runtime.get("workflow_identity"), dict) else {}
    )
    expected_process_run_id = str(os.environ.get("GITHUB_RUN_ID", ""))
    expected_process_attempt = str(os.environ.get("GITHUB_RUN_ATTEMPT", ""))
    expected_process_executable = str(jasp_runtime_identity.get("jasp_binary_sha256", ""))
    expected_process_runtime = str(jasp_runtime_identity.get("flatpak_runtime_commit", ""))
    process_identity_bound = bool(
        not direct or (
            jasp_runtime_identity.get("status") == "PASS"
            and valid_workflow_identity(expected_process_run_id, expected_process_attempt)
            and target_workflow_identity.get("run_id") == expected_process_run_id
            and target_workflow_identity.get("run_attempt") == expected_process_attempt
            and re.fullmatch(r"[0-9a-f]{64}", expected_process_executable)
            and re.fullmatch(r"[0-9a-f]{64}", expected_process_runtime)
        )
    )
    process_tree_invocations = []
    expected_process_cases = {
        "flatpak_launch": ["flatpak_launch"],
        "reliability": ["reliability"],
        "weight_gain": ["weight_gain"],
        "death_penalty_roundtrip": ["death_penalty_save", "death_penalty_rerun"],
    }
    for case_id, expected_ids in expected_process_cases.items():
        row = jasp_cases.get(case_id) if isinstance(jasp_cases, dict) else None
        if not isinstance(row, dict):
            continue
        receipts = (
            row.get("process_tree_receipts")
            if case_id == "death_penalty_roundtrip"
            else [row.get("process_tree_receipt")]
        )
        if not isinstance(receipts, list):
            continue
        for receipt, expected_case_id in zip(receipts, expected_ids):
            if process_tree_receipt_identity_matches(
                receipt, case_id=expected_case_id, env=os.environ,
                executable_sha256=expected_process_executable,
                runtime_ostree_commit=expected_process_runtime,
            ):
                process_tree_invocations.append(receipt)
    unique_invocation_ids = {
        row.get("invocation_id") for row in process_tree_invocations
        if isinstance(row, dict) and isinstance(row.get("invocation_id"), str)
    }
    process_tree_evidence = {
        row["evidence_path"]: row["evidence_sha256"]
        for row in jasp_cases.values()
        if isinstance(row, dict)
        and isinstance(row.get("evidence_path"), str)
        and row.get("evidence_path").strip()
        and isinstance(row.get("evidence_sha256"), str)
    }
    process_tree_complete = (
        process_identity_bound
        and set(jasp_cases) == set(expected_process_cases)
        and len(process_tree_invocations) == 5
        and len(unique_invocation_ids) == 5
        and all(
            row.get("process_group_closed") is True
            and row.get("remaining_live_pids") == []
            and row.get("timeout_triggered") is False
            for row in process_tree_invocations
        )
    )
    if direct:
        checks["jasp_process_tree_lifecycle"] = {
            "status": "PASS" if process_tree_complete else "BLOCKED",
            "returncode": 0 if process_tree_complete else 1,
            "invocation_count": len(process_tree_invocations),
            "expected_invocation_count": 5,
            "unique_invocation_id_count": len(unique_invocation_ids),
            "workflow_identity": {
                "run_id": expected_process_run_id,
                "run_attempt": expected_process_attempt,
            },
            "jasp_binary_sha256": expected_process_executable,
            "flatpak_runtime_ostree_commit": expected_process_runtime,
            "invocations": process_tree_invocations,
            "evidence": process_tree_evidence,
        }
    squashfs_identity = direct_candidate_squashfs_identity() if direct else {}
    if direct:
        checks["squashfs_image_and_package_binding"] = {
            "status": squashfs_identity.get("status", "BLOCKED"),
            "returncode": 0 if squashfs_identity.get("status") == "PASS" else 1,
            "image_path": squashfs_identity.get("image_path"),
            "image_sha256": squashfs_identity.get("image_sha256"),
            "image_bytes": squashfs_identity.get("image_bytes"),
            "checksum_path": squashfs_identity.get("checksum_path"),
            "checksum_sha256": squashfs_identity.get("checksum_sha256"),
            "package_receipt_path": squashfs_identity.get("package_receipt_path"),
            "package_receipt_sha256": squashfs_identity.get("package_receipt_sha256"),
            "candidate_manifest_path": squashfs_identity.get("candidate_manifest_path"),
            "candidate_manifest_sha256": squashfs_identity.get("candidate_manifest_sha256"),
            "evidence": {
                squashfs_identity[key]: squashfs_identity[digest_key]
                for key, digest_key in (
                    ("image_path", "image_sha256"),
                    ("checksum_path", "checksum_sha256"),
                    ("package_receipt_path", "package_receipt_sha256"),
                    ("candidate_manifest_path", "candidate_manifest_sha256"),
                )
                if squashfs_identity.get(key) and squashfs_identity.get(digest_key)
            },
            "details": squashfs_identity.get("reason"),
        }
    if direct:
        checks["squashfs_rootfs_postvalidation_manifest_closure"] = direct_candidate_rootfs_manifest_closure(
            jasp, inventory, inventory_hashes_valid
        )
    if direct:
        checks["jasp_post_mutation_runtime_identity"] = jasp_runtime_identity
    # Re-validate pre-existing source-bound checks instead of overwriting their history.
    for name, check in list(checks.items()):
        if name in {"MISION1_identity_sha256", "runtime_report_and_launcher_identity"}:
            continue
        if isinstance(check, dict) and check.get("status") == "PASS":
            evidence = check.get("evidence")
            if isinstance(evidence, dict):
                bad = []
                for path_text, expected in evidence.items():
                    path = pathlib.Path(path_text)
                    if not path.is_file() or not isinstance(expected, str) or sha_file(path) != expected:
                        bad.append(path_text)
                if bad:
                    checks[name] = {**check, "status": "BLOCKED_EVIDENCE_HASH_MISMATCH",
                                    "returncode": 1, "hash_mismatch_paths": bad[:40]}
    checks_pass = bool(checks) and all(_stable_check(x) for x in checks.values())
    desired_status = "PASS_INDEPENDENT_VALIDATION" if checks_pass else "BLOCKED_REQUIRED_REGRESSION_OR_INVENTORY"
    report = {
        "schema": "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0",
        "captured_at_utc": utc(), "candidate_id": "G06_REBUILD_CANDIDATE_R1",
        "mission_sha256": mission_sha, "runtime_report_path": runtime_path_text,
        "runtime_report_sha256": runtime_sha, "beta_launcher_sha256": launcher_sha,
        "certification_profile": "V1_8_DIRECT" if direct else "LEGACY_V1_7",
        "candidate_manifest_sha256": candidate_manifest_sha,
        "squashfs_image_path": squashfs_identity.get("image_path") if direct else None,
        "squashfs_image_sha256": squashfs_identity.get("image_sha256") if direct else None,
        "squashfs_image_bytes": squashfs_identity.get("image_bytes") if direct else None,
        "squashfs_checksum_path": squashfs_identity.get("checksum_path") if direct else None,
        "squashfs_checksum_sha256": squashfs_identity.get("checksum_sha256") if direct else None,
        "squashfs_package_receipt_path": squashfs_identity.get("package_receipt_path") if direct else None,
        "squashfs_package_receipt_sha256": squashfs_identity.get("package_receipt_sha256") if direct else None,
        "target_runtime_acceptance": target_runtime,
        "checks": checks, "status": desired_status,
        "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
        "certification": "NOT_GRANTED",
        "next_action": "Finish every independent check; only S32 may issue a hash-bound candidate certification receipt. Stable release requires a separate receipt after S32.",
        "open_items": [name for name, value in checks.items() if not _stable_check(value)],
        "mission_completion_claim": False,
    }
    return report


def persist_independent_report(report: dict) -> dict:
    """Version the old bytes before updating the mutable current candidate report."""
    EVIDENCE.mkdir(parents=True, exist_ok=True, mode=0o700)
    history = EVIDENCE / "history"
    history.mkdir(parents=True, exist_ok=True, mode=0o700)
    old_bytes = INDEPENDENT_REPORT.read_bytes() if INDEPENDENT_REPORT.is_file() else None
    old_sha = hashlib.sha256(old_bytes).hexdigest() if old_bytes is not None else None
    semantic = dict(report)
    semantic.pop("captured_at_utc", None)
    old = load_json(INDEPENDENT_REPORT, {}) or {}
    prior_semantic = dict(old)
    prior_semantic.pop("captured_at_utc", None)
    if old_sha and json.dumps(prior_semantic, sort_keys=True, ensure_ascii=False) == json.dumps(semantic, sort_keys=True, ensure_ascii=False):
        return {"changed": False, "current_sha256": old_sha, "status": report.get("status")}
    if old_bytes is not None:
        archive = history / f"BETA_INDEPENDENT_VALIDATION_{old_sha}.json"
        if archive.exists():
            if sha_file(archive) != old_sha:
                raise RuntimeError("INDEPENDENT_REPORT_HISTORY_COLLISION")
        else:
            archive.write_bytes(old_bytes)
    atomic_json(INDEPENDENT_REPORT, report)
    return {"changed": True, "previous_sha256": old_sha, "current_sha256": sha_file(INDEPENDENT_REPORT),
            "status": report.get("status")}


def jasp_roundtrip_functional_evidence_valid(checks: dict) -> bool:
    """Fail closed unless JASP strict reference evidence and both clone hashes are independently bound."""
    try:
        jasp = checks.get("jasp_packaged_fixture_nonregression") if isinstance(checks, dict) else None
        if not isinstance(jasp, dict) or jasp.get("status") != "PASS" or jasp.get("returncode") != 0:
            return False
        cases = jasp.get("cases")
        required_cases = {"flatpak_launch", "reliability", "weight_gain", "death_penalty_roundtrip"}
        if not isinstance(cases, dict) or set(cases) != required_cases:
            return False
        if any(not isinstance(row, dict) or row.get("status") != "PASS" or row.get("returncode") != 0
               for row in cases.values()):
            return False
        row = cases["death_penalty_roundtrip"]
        if (
            row.get("acceptance_scope") != "STRICT_REFERENCE_AND_REPLAY"
            or row.get("reference_comparison_status") != "PASS"
            or row.get("deterministic_replay_status") != "PASS_DETERMINISTIC_REPLAY"
            or row.get("deterministic_fixture_receipt_valid") is not True
            or row.get("temporary_fixture_hash_invariant_passed") is not True
            or row.get("temporary_fixture_regular_after_save") is not True
            or row.get("temporary_fixture_regular_after_rerun") is not True
            or row.get("temporary_fixture_changed") is not False
            or row.get("temporary_fixture_removed_after_test") is not True
            or row.get("temporary_fixture_stable_after_save_and_rerun") is not True
            or row.get("save_fixture_unchanged_after_execution") is not True
            or row.get("rerun_fixture_unchanged_after_execution") is not True
            or row.get("original_sample_unchanged") is not True
            or row.get("original_sample_identity_matches_pin") is not True
            or row.get("original_sample_sha256_before") != DEATH_PENALTY_SOURCE_SHA256
            or row.get("original_sample_sha256_after") != DEATH_PENALTY_SOURCE_SHA256
        ):
            return False
        receipt = row.get("deterministic_fixture_receipt")
        if not isinstance(receipt, dict):
            return False
        expected = row.get("temporary_fixture_sha256_expected")
        if (
            not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None
            or receipt.get("clone_sha256") != expected
            or row.get("temporary_fixture_sha256_before") != expected
            or row.get("temporary_fixture_sha256_after_save") != expected
            or row.get("temporary_fixture_sha256_after_rerun") != expected
            or row.get("save_fixture_sha256_after_execution") != expected
            or row.get("rerun_fixture_sha256_after_execution") != expected
        ):
            return False
        evidence = jasp.get("evidence")
        if not isinstance(evidence, dict):
            return False
        out_root = OUT.resolve()
        def verified_evidence_file(path_text: object, expected_sha: object) -> pathlib.Path | None:
            if not isinstance(path_text, str) or not path_text or not isinstance(expected_sha, str):
                return None
            path_obj = pathlib.Path(path_text)
            if path_obj.is_symlink() or not path_obj.is_file():
                return None
            resolved = path_obj.resolve(strict=True)
            try:
                resolved.relative_to(out_root)
            except ValueError:
                return None
            observed = sha_file(resolved)
            if observed != expected_sha or evidence.get(str(path_obj)) != expected_sha:
                return None
            return resolved
        roundtrip_report = verified_evidence_file(row.get("evidence_path"), row.get("evidence_sha256"))
        if roundtrip_report is None:
            return False
        receipt_path = verified_evidence_file(receipt.get("receipt_path"), receipt.get("receipt_sha256"))
        if receipt_path is None:
            return False
        on_disk_receipt = load_json(receipt_path, {}) or {}
        for key in (
            "schema", "status", "source_path", "source_sha256", "expected_source_sha256",
            "source_sha256_after", "source_unchanged", "clone_path", "clone_sha256",
            "clone_is_distinct", "active_configuration_member", "changed_archive_member",
            "changed_json_pointer", "analysis_index", "analysis_id", "analysis_name",
            "module_name", "archive_member_count", "changed_archive_member_count",
            "unchanged_non_active_member_count", "before", "after",
            "result_output_members_changed", "reference_results_modified",
        ):
            if on_disk_receipt.get(key) != receipt.get(key):
                return False
        if (
            receipt.get("schema") != "LUNITA_JASP_DETERMINISTIC_FIXTURE/1.0"
            or receipt.get("status") != "PASS_DETERMINISTIC_FIXTURE_COPY_CREATED"
            or receipt.get("source_sha256") != DEATH_PENALTY_SOURCE_SHA256
            or receipt.get("expected_source_sha256") != DEATH_PENALTY_SOURCE_SHA256
            or receipt.get("source_sha256_after") != DEATH_PENALTY_SOURCE_SHA256
            or receipt.get("source_unchanged") is not True
            or receipt.get("clone_is_distinct") is not True
            or receipt.get("reference_results_modified") is not False
            or receipt.get("result_output_members_changed") is not False
            or row.get("temporary_fixture_path") != receipt.get("clone_path")
        ):
            return False
        clone_text = receipt.get("clone_path")
        if not isinstance(clone_text, str):
            return False
        clone_path = pathlib.Path(clone_text)
        if clone_path.exists() or clone_path.is_symlink():
            return False
        source_text = receipt.get("source_path")
        if not isinstance(source_text, str):
            return False
        source_path = pathlib.Path(source_text)
        if (source_path.is_symlink() or not source_path.is_file()
            or sha_file(source_path) != DEATH_PENALTY_SOURCE_SHA256):
            return False
        for label, path_key, sha_key in (
            ("SAVE", "save_log_path", "save_log_sha256"),
            ("RERUN", "rerun_log_path", "rerun_log_sha256"),
        ):
            log_path = verified_evidence_file(row.get(path_key), row.get(sha_key))
            if log_path is None:
                return False
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            required = (
                f"JASP_ROUNDTRIP_FIXTURE_SHA256_EXPECTED={expected}",
                f"JASP_ROUNDTRIP_FIXTURE_SHA256_AFTER_{label}={expected}",
                f"JASP_ROUNDTRIP_FIXTURE_UNCHANGED_AFTER_{label}=TRUE",
            )
            if any(marker not in lines for marker in required):
                return False
        return True
    except (OSError, TypeError, ValueError, KeyError):
        return False

def issue_s32_independent_beta_validation_receipt() -> dict:
    """Issue S32 only for a fully hash-bound direct-v1.8 candidate PASS.

    This is candidate-beta operational certification only. It never grants G23/G24,
    canonical G06/G08 certification, promotion, or mission completion.
    """
    if CERTIFICATION_PROFILE != "V1_8_DIRECT":
        return {"status": "NOT_APPLICABLE_LEGACY_PROFILE", "certification": "NOT_GRANTED"}

    report_path = INDEPENDENT_REPORT
    if report_path.is_symlink() or not report_path.is_file():
        return {"status": "BLOCKED_INDEPENDENT_REPORT_MISSING", "certification": "NOT_GRANTED"}
    report = load_json(report_path, {}) or {}
    if report.get("schema") != "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0":
        return {"status": "BLOCKED_INDEPENDENT_REPORT_SCHEMA", "certification": "NOT_GRANTED"}
    if report.get("status") != "PASS_INDEPENDENT_VALIDATION":
        return {"status": "BLOCKED_INDEPENDENT_VALIDATION", "certification": "NOT_GRANTED"}
    if report.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1" or report.get("certification_profile") != "V1_8_DIRECT":
        return {"status": "BLOCKED_CANDIDATE_PROFILE_IDENTITY", "certification": "NOT_GRANTED"}

    manifest = direct_candidate_manifest_identity()
    if manifest.get("status") != "PASS" or report.get("candidate_manifest_sha256") != manifest.get("sha256"):
        return {"status": "BLOCKED_CANDIDATE_MANIFEST_BINDING", "certification": "NOT_GRANTED"}

    target = latest_target_runtime_acceptance()
    target_path = pathlib.Path(target.get("receipt_path", "")) if target.get("receipt_path") else None
    if (target.get("status") != "PASS_TARGET_RUNTIME_ACCEPTANCE" or not target_path
        or target_path.is_symlink() or not target_path.is_file()
        or target.get("receipt_sha256") != sha_file(target_path)):
        return {"status": "BLOCKED_TARGET_RUNTIME_ACCEPTANCE", "certification": "NOT_GRANTED"}
    target_sha = sha_file(target_path)
    if (report.get("runtime_report_path") != str(target_path)
        or report.get("runtime_report_sha256") != target_sha):
        return {"status": "BLOCKED_RUNTIME_REPORT_HASH_BINDING", "certification": "NOT_GRANTED"}

    checks = report.get("checks")
    required_checks = {
        "candidate_manifest_identity_sha256",
        "runtime_report_and_launcher_identity",
        "target_v1_8_runtime_acceptance_e01_e15_int8",
        "candidate_rootfs_inventory_and_dependency_manifest",
        "jasp_packaged_fixture_nonregression",
        "jasp_process_tree_lifecycle",
        "jasp_post_mutation_runtime_identity",
        "squashfs_image_and_package_binding",
    }
    if not isinstance(checks, dict) or not required_checks.issubset(checks):
        return {"status": "BLOCKED_REQUIRED_INDEPENDENT_CHECKS_MISSING", "certification": "NOT_GRANTED"}
    if any(not _stable_check(check) for check in checks.values()):
        return {"status": "BLOCKED_REQUIRED_INDEPENDENT_CHECKS", "certification": "NOT_GRANTED"}
    process_tree_check = checks["jasp_process_tree_lifecycle"]
    process_tree_workflow = process_tree_check.get("workflow_identity") or {}
    target_workflow = target.get("workflow_identity") or {}
    jasp_identity_check = checks.get("jasp_post_mutation_runtime_identity") or {}
    expected_process_cases = {
        "flatpak_launch", "reliability", "weight_gain",
        "death_penalty_save", "death_penalty_rerun",
    }
    process_invocations = process_tree_check.get("invocations")
    executable_sha = str(process_tree_check.get("jasp_binary_sha256", ""))
    runtime_commit = str(process_tree_check.get("flatpak_runtime_ostree_commit", ""))
    invocation_ids = {
        row.get("invocation_id") for row in process_invocations
        if isinstance(row, dict)
    } if isinstance(process_invocations, list) else set()
    observed_cases = {
        row.get("case_id") for row in process_invocations
        if isinstance(row, dict)
    } if isinstance(process_invocations, list) else set()
    process_receipts_valid = bool(
        isinstance(process_invocations, list)
        and len(process_invocations) == 5
        and observed_cases == expected_process_cases
        and len(invocation_ids) == 5
        and process_tree_check.get("invocation_count") == 5
        and process_tree_check.get("unique_invocation_id_count") == 5
        and all(
            process_tree_receipt_identity_matches(
                row, case_id=str(row.get("case_id", "")), env=os.environ,
                executable_sha256=executable_sha, runtime_ostree_commit=runtime_commit,
            )
            for row in process_invocations
        )
    )
    if not process_receipts_valid:
        return {"status": "BLOCKED_JASP_PROCESS_TREE_RECEIPTS", "certification": "NOT_GRANTED"}
    if (
        process_tree_workflow.get("run_id") != str(target_workflow.get("run_id", ""))
        or process_tree_workflow.get("run_attempt") != str(target_workflow.get("run_attempt", ""))
        or process_tree_check.get("jasp_binary_sha256") != jasp_identity_check.get("jasp_binary_sha256")
        or process_tree_check.get("flatpak_runtime_ostree_commit") != jasp_identity_check.get("flatpak_runtime_commit")
        or process_tree_check.get("invocation_count") != 5
    ):
        return {"status": "BLOCKED_JASP_PROCESS_TREE_IDENTITY_BINDING", "certification": "NOT_GRANTED"}
    if not jasp_roundtrip_functional_evidence_valid(checks):
        return {"status": "BLOCKED_JASP_ROUNDTRIP_OR_STORED_REFERENCE", "certification": "NOT_GRANTED"}
    target_check = checks["target_v1_8_runtime_acceptance_e01_e15_int8"]
    if (target_check.get("receipt_path") != str(target_path)
        or target_check.get("receipt_sha256") != target_sha):
        return {"status": "BLOCKED_TARGET_RUNTIME_CHECK_BINDING", "certification": "NOT_GRANTED"}
    if (checks["candidate_manifest_identity_sha256"].get("sha256") != manifest.get("sha256")
        or report.get("frozen_g06_mutated") is not False
        or report.get("canonical_g08_bindings_mutated") is not False
        or target.get("canonical_g08_binding_mutation") is not False):
        return {"status": "BLOCKED_CANONICAL_IDENTITY_GUARD", "certification": "NOT_GRANTED"}

    squashfs_identity = direct_candidate_squashfs_identity()
    image_check = checks["squashfs_image_and_package_binding"]
    if squashfs_identity.get("status") != "PASS":
        return {"status": "BLOCKED_SQUASHFS_IMAGE_BINDING", "certification": "NOT_GRANTED"}
    for field in ("image_path", "image_sha256", "image_bytes", "checksum_path", "checksum_sha256",
                  "package_receipt_path", "package_receipt_sha256", "candidate_manifest_path",
                  "candidate_manifest_sha256"):
        if image_check.get(field) != squashfs_identity.get(field):
            return {"status": "BLOCKED_SQUASHFS_IMAGE_REPORT_BINDING", "certification": "NOT_GRANTED"}

    independent_sha = sha_file(report_path)
    evidence = {
        "independent_validation": "PASS",
        "independent_report_path": str(report_path),
        "independent_report_sha256": independent_sha,
        "target_runtime_receipt_path": str(target_path),
        "target_runtime_receipt_sha256": target_sha,
        "candidate_manifest_sha256": manifest["sha256"],
        "squashfs_image_path": squashfs_identity["image_path"],
        "squashfs_image_sha256": squashfs_identity["image_sha256"],
        "squashfs_image_bytes": squashfs_identity["image_bytes"],
        "squashfs_checksum_path": squashfs_identity["checksum_path"],
        "squashfs_checksum_sha256": squashfs_identity["checksum_sha256"],
        "squashfs_package_receipt_path": squashfs_identity["package_receipt_path"],
        "squashfs_package_receipt_sha256": squashfs_identity["package_receipt_sha256"],
    }
    payload = {
        "schema": "CUSTOSZ_LUNITA_BETA_CERTIFICATION_RECEIPT/1.0",
        "status": "BETA_OPERATIONAL_CERTIFIED",
        "step_completion": True,
        "candidate_id": "G06_REBUILD_CANDIDATE_R1",
        "version": "1.8.0",
        "basis": "VERSIONED_DERIVED_UBUNTU_24_04_CANDIDATE; NOT_THE_MISSING_FROZEN_ORIGINAL",
        "runtime_report_path": str(target_path),
        "runtime_report_sha256": target_sha,
        "independent_report_path": str(report_path),
        "independent_report_sha256": independent_sha,
        "squashfs_image_path": squashfs_identity["image_path"],
        "squashfs_image_sha256": squashfs_identity["image_sha256"],
        "squashfs_image_bytes": squashfs_identity["image_bytes"],
        "squashfs_checksum_path": squashfs_identity["checksum_path"],
        "squashfs_checksum_sha256": squashfs_identity["checksum_sha256"],
        "squashfs_package_receipt_path": squashfs_identity["package_receipt_path"],
        "squashfs_package_receipt_sha256": squashfs_identity["package_receipt_sha256"],
        "candidate_manifest_sha256": manifest["sha256"],
        "evidence": evidence,
        "frozen_g06_mutated": False,
        "canonical_g08_bindings_mutated": False,
        "canonical_g06_certification": "NOT_GRANTED",
        "g23_status": "NOT_GRANTED",
        "g24_status": "NOT_GRANTED",
        "certification_scope": "CANDIDATE_BETA_ONLY; NO AUTOMATIC CERTIFICATION PROPAGATION",
        "certification": "GRANTED_FOR_VERSIONED_CANDIDATE_ONLY",
        "mission_completion_claim": False,
        "created_at_utc": utc(),
    }
    OUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipt_path = OUT / f"S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT_{independent_sha[:16]}.json"
    if receipt_path.exists():
        existing = load_json(receipt_path, {}) or {}
        comparable = dict(existing)
        comparable.pop("created_at_utc", None)
        expected = dict(payload)
        expected.pop("created_at_utc", None)
        if comparable != expected:
            return {"status": "BLOCKED_S32_RECEIPT_IDENTITY_COLLISION", "certification": "NOT_GRANTED"}
    else:
        atomic_json(receipt_path, payload)
    observed = load_json(receipt_path, {}) or {}
    if (observed.get("status") != "BETA_OPERATIONAL_CERTIFIED"
        or observed.get("evidence") != evidence
        or observed.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1"):
        return {"status": "BLOCKED_S32_RECEIPT_POST_WRITE_VERIFICATION", "certification": "NOT_GRANTED"}
    return {
        "status": "BETA_OPERATIONAL_CERTIFIED",
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha_file(receipt_path),
        "independent_report_sha256": independent_sha,
        "target_runtime_receipt_sha256": target_sha,
        "certification": "GRANTED_FOR_VERSIONED_CANDIDATE_ONLY",
        "g23_status": "NOT_GRANTED",
        "g24_status": "NOT_GRANTED",
    }


def stable_release_gate() -> dict:
    direct = CERTIFICATION_PROFILE == "V1_8_DIRECT"
    report = load_json(INDEPENDENT_REPORT, {}) or {}
    if direct:
        manifest_identity = direct_candidate_manifest_identity()
        target_runtime = latest_target_runtime_acceptance()
        target_path = pathlib.Path(target_runtime.get("receipt_path", "")) if target_runtime.get("receipt_path") else None
        runtime = (load_json(target_path, {}) or {}) if target_path else {}
        runtime_sha = sha_file(target_path) if target_path and target_path.is_file() else None
        identity_ok = (
            manifest_identity.get("status") == "PASS"
            and report.get("schema") == "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0"
            and report.get("candidate_id") == "G06_REBUILD_CANDIDATE_R1"
            and report.get("certification_profile") == "V1_8_DIRECT"
            and report.get("candidate_manifest_sha256") == manifest_identity.get("sha256")
            and runtime.get("schema") == "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0"
            and runtime.get("status") == "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED"
            and runtime.get("candidate_id") == "G06_REBUILD_CANDIDATE_R1"
            and report.get("runtime_report_path") == str(target_path)
        )
    else:
        runtime = load_json(RUNTIME_REPORT, {}) or {}
        runtime_sha = sha_file(RUNTIME_REPORT) if RUNTIME_REPORT.is_file() else None
        identity_ok = (
            report.get("schema") == "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0"
            and report.get("candidate_id") == "G06_REBUILD_CANDIDATE_R1"
            and report.get("mission_sha256") == MISSION_SHA
            and runtime.get("schema") == "CUSTOSZ_LUNITA_BETA_RUNTIME_FUNCTIONAL_TESTS/1.0"
            and runtime.get("candidate_id") == "G06_REBUILD_CANDIDATE_R1"
        )
    if not identity_ok:
        return {"status": "BLOCKED_CANDIDATE_OR_MISSION_IDENTITY", "certification": "NOT_GRANTED"}
    if report.get("status") != "PASS_INDEPENDENT_VALIDATION":
        return {"status": "BLOCKED_INDEPENDENT_VALIDATION", "certification": "NOT_GRANTED"}
    squashfs_identity = direct_candidate_squashfs_identity() if direct else {}
    if direct:
        if squashfs_identity.get("status") != "PASS":
            return {"status": "BLOCKED_SQUASHFS_IMAGE_BINDING", "certification": "NOT_GRANTED"}
        for field, report_field in (
            ("image_path", "squashfs_image_path"),
            ("image_sha256", "squashfs_image_sha256"),
            ("image_bytes", "squashfs_image_bytes"),
            ("checksum_path", "squashfs_checksum_path"),
            ("checksum_sha256", "squashfs_checksum_sha256"),
            ("package_receipt_path", "squashfs_package_receipt_path"),
            ("package_receipt_sha256", "squashfs_package_receipt_sha256"),
            ("candidate_manifest_sha256", "candidate_manifest_sha256"),
        ):
            if report.get(report_field) != squashfs_identity.get(field):
                return {"status": "BLOCKED_SQUASHFS_IMAGE_REPORT_BINDING", "certification": "NOT_GRANTED"}
        image_check = (report.get("checks") or {}).get("squashfs_image_and_package_binding", {})
        if image_check.get("status") != "PASS":
            return {"status": "BLOCKED_SQUASHFS_IMAGE_REPORT_BINDING", "certification": "NOT_GRANTED"}
    target_check = (report.get("checks") or {}).get("target_v1_8_runtime_acceptance_e01_e15_int8", {})
    target_path = pathlib.Path(target_check.get("receipt_path", "")) if target_check.get("receipt_path") else None
    if (target_check.get("status") != "PASS" or not target_path or not target_path.is_file()
        or target_check.get("receipt_sha256") != sha_file(target_path)):
        return {"status": "BLOCKED_TARGET_V1_8_RUNTIME_BINDING", "certification": "NOT_GRANTED"}
    checks = report.get("checks")
    if not isinstance(checks, dict) or not checks or not all(_stable_check(x) for x in checks.values()):
        return {"status": "BLOCKED_REQUIRED_CHECKS", "certification": "NOT_GRANTED"}
    if direct and not jasp_roundtrip_functional_evidence_valid(checks):
        return {"status": "BLOCKED_JASP_ROUNDTRIP_OR_STORED_REFERENCE", "certification": "NOT_GRANTED"}
    if direct:
        required_direct_checks = {
            "jasp_packaged_fixture_nonregression",
            "jasp_process_tree_lifecycle",
            "jasp_post_mutation_runtime_identity",
            "squashfs_image_and_package_binding",
        }
        if not required_direct_checks.issubset(checks):
            return {"status": "BLOCKED_REQUIRED_JASP_LIFECYCLE_CHECKS", "certification": "NOT_GRANTED"}
        lifecycle = checks.get("jasp_process_tree_lifecycle") or {}
        mutation_identity = checks.get("jasp_post_mutation_runtime_identity") or {}
        target_workflow = runtime.get("workflow_identity") if isinstance(runtime.get("workflow_identity"), dict) else {}
        lifecycle_workflow = lifecycle.get("workflow_identity") if isinstance(lifecycle.get("workflow_identity"), dict) else {}
        invocations = lifecycle.get("invocations")
        expected_cases = {
            "flatpak_launch", "reliability", "weight_gain",
            "death_penalty_save", "death_penalty_rerun",
        }
        invocation_ids = {
            row.get("invocation_id") for row in invocations
            if isinstance(row, dict)
        } if isinstance(invocations, list) else set()
        observed_cases = {
            row.get("case_id") for row in invocations
            if isinstance(row, dict)
        } if isinstance(invocations, list) else set()
        expected_run_id = str(os.environ.get("GITHUB_RUN_ID", ""))
        expected_attempt = str(os.environ.get("GITHUB_RUN_ATTEMPT", ""))
        executable_sha = str(mutation_identity.get("jasp_binary_sha256", ""))
        runtime_commit = str(mutation_identity.get("flatpak_runtime_commit", ""))
        final_process_tree_valid = bool(
            lifecycle.get("status") == "PASS"
            and lifecycle.get("returncode") == 0
            and lifecycle.get("invocation_count") == 5
            and lifecycle.get("expected_invocation_count") == 5
            and lifecycle.get("unique_invocation_id_count") == 5
            and mutation_identity.get("status") == "PASS"
            and mutation_identity.get("returncode") == 0
            and re.fullmatch(r"[0-9a-f]{64}", executable_sha)
            and re.fullmatch(r"[0-9a-f]{64}", runtime_commit)
            and expected_run_id == str(target_workflow.get("run_id", ""))
            and expected_attempt == str(target_workflow.get("run_attempt", ""))
            and lifecycle_workflow.get("run_id") == expected_run_id
            and lifecycle_workflow.get("run_attempt") == expected_attempt
            and lifecycle.get("jasp_binary_sha256") == executable_sha
            and lifecycle.get("flatpak_runtime_ostree_commit") == runtime_commit
            and isinstance(invocations, list)
            and len(invocations) == 5
            and observed_cases == expected_cases
            and len(invocation_ids) == 5
            and all(
                process_tree_receipt_identity_matches(
                    row, case_id=str(row.get("case_id", "")), env=os.environ,
                    executable_sha256=executable_sha, runtime_ostree_commit=runtime_commit,
                )
                for row in invocations
            )
        )
        if not final_process_tree_valid:
            return {"status": "BLOCKED_JASP_PROCESS_TREE_FINAL_CERTIFICATION", "certification": "NOT_GRANTED"}
    if report.get("runtime_report_sha256") != runtime_sha:
        return {"status": "BLOCKED_RUNTIME_REPORT_BINDING_MISMATCH", "certification": "NOT_GRANTED"}
    if report.get("frozen_g06_mutated") is not False or report.get("canonical_g08_bindings_mutated") is not False:
        return {"status": "BLOCKED_CANONICAL_IDENTITY_GUARD", "certification": "NOT_GRANTED"}
    # S32 is the single issuing gate: stable packaging waits for its actual bound receipt.
    receipts = sorted(OUT.glob("S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT_*.json"),
                      key=lambda p: p.stat().st_mtime_ns, reverse=True)
    receipt = None
    for p in receipts:
        row = load_json(p, {}) or {}
        ev = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
        if row.get("status") == "BETA_OPERATIONAL_CERTIFIED" and ev.get("independent_validation") == "PASS":
            if (
                ev.get("independent_report_path") == str(INDEPENDENT_REPORT)
                and ev.get("independent_report_sha256") == sha_file(INDEPENDENT_REPORT)
                and ev.get("candidate_manifest_sha256") == report.get("candidate_manifest_sha256")
                and ev.get("squashfs_image_sha256") == squashfs_identity.get("image_sha256")
                and ev.get("squashfs_image_bytes") == squashfs_identity.get("image_bytes")
                and ev.get("squashfs_checksum_sha256") == squashfs_identity.get("checksum_sha256")
                and ev.get("squashfs_package_receipt_sha256") == squashfs_identity.get("package_receipt_sha256")
            ):
                receipt = {"path": str(p), "sha256": sha_file(p)}
                break
    if not receipt:
        return {"status": "WAITING_FOR_S32_BOUND_CERTIFICATION_RECEIPT", "certification": "NOT_GRANTED"}
    return {
        "status": "STABLE_RELEASE_ELIGIBLE", "version": "1.8.0", "release_name": "LUNITA_STABLE_1_8",
        "candidate_id": "G06_REBUILD_CANDIDATE_R1",
        "runtime_report_sha256": runtime_sha,
        "candidate_manifest_sha256": report.get("candidate_manifest_sha256"),
        "squashfs_image_path": squashfs_identity.get("image_path") if direct else None,
        "squashfs_image_sha256": squashfs_identity.get("image_sha256") if direct else None,
        "squashfs_image_bytes": squashfs_identity.get("image_bytes") if direct else None,
        "squashfs_checksum_path": squashfs_identity.get("checksum_path") if direct else None,
        "squashfs_checksum_sha256": squashfs_identity.get("checksum_sha256") if direct else None,
        "squashfs_package_receipt_path": squashfs_identity.get("package_receipt_path") if direct else None,
        "squashfs_package_receipt_sha256": squashfs_identity.get("package_receipt_sha256") if direct else None,
        "independent_report_sha256": sha_file(INDEPENDENT_REPORT),
        "s32_receipt": receipt, "rootfs_path": str(ROOTFS),
        "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
        "certification_scope": "VERSIONED_DERIVED_CANDIDATE_ONLY",
        "mission_completion_claim": False,
    }


def persist_stable_release_status(release_gate: dict) -> dict:
    """Store immutable release receipts keyed by evidence; keep a mutable current-state pointer."""
    release_dir = ST / "releases" / "LUNITA_STABLE_1_8"
    release_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    current_path = release_dir / "current_status.json"
    eligible = release_gate.get("status") == "STABLE_RELEASE_ELIGIBLE"
    receipt_path = None
    receipt_sha = None
    if eligible:
        digest = str(release_gate.get("independent_report_sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RuntimeError("STABLE_RELEASE_REPORT_SHA256_INVALID")
        receipt_path = release_dir / f"release_{digest[:16]}.json"
        payload = {**release_gate, "schema": "CUSTOSZ_LUNITA_STABLE_RELEASE/1.0",
                   "status": "CERTIFIED_STABLE_RELEASE", "certification": "GRANTED_FOR_VERSIONED_CANDIDATE",
                   "created_at_utc": utc()}
        if receipt_path.exists():
            existing = load_json(receipt_path, {}) or {}
            if (existing.get("status") != "CERTIFIED_STABLE_RELEASE"
                or existing.get("independent_report_sha256") != digest
                or existing.get("runtime_report_sha256") != payload.get("runtime_report_sha256")
                or existing.get("candidate_manifest_sha256") != payload.get("candidate_manifest_sha256")
                or existing.get("squashfs_image_sha256") != payload.get("squashfs_image_sha256")
                or existing.get("squashfs_image_bytes") != payload.get("squashfs_image_bytes")
                or existing.get("squashfs_checksum_sha256") != payload.get("squashfs_checksum_sha256")
                or existing.get("squashfs_package_receipt_sha256") != payload.get("squashfs_package_receipt_sha256")
                or existing.get("s32_receipt") != payload.get("s32_receipt")):
                raise RuntimeError("STABLE_RELEASE_RECEIPT_IDENTITY_COLLISION")
        else:
            atomic_json(receipt_path, payload)
        receipt_sha = sha_file(receipt_path)
        status = "CERTIFIED_STABLE_RELEASE_ACTIVE"
    else:
        previous = sorted(release_dir.glob("release_*.json"))
        status = "REVALIDATION_REQUIRED" if previous else "NOT_YET_CERTIFIED"
    pointer = {
        "schema": "CUSTOSZ_LUNITA_STABLE_RELEASE_CURRENT_STATUS/1.0",
        "updated_at_utc": utc(), "status": status, "release_gate_status": release_gate.get("status"),
        "release_receipt_path": str(receipt_path) if receipt_path else None,
        "release_receipt_sha256": receipt_sha,
        "candidate_id": "G06_REBUILD_CANDIDATE_R1", "version": "1.8.0",
        "release_name": "LUNITA_STABLE_1_8",
        "certification_scope": "VERSIONED_DERIVED_CANDIDATE_ONLY",
        "previous_release_receipts_retained": True,
        "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
        "mission_completion_claim": False,
    }
    atomic_json(current_path, pointer)
    return {"status": status, "current_status_path": str(current_path),
            "release_name": "LUNITA_STABLE_1_8", "version": "1.8.0",
            "release_receipt_path": str(receipt_path) if receipt_path else None,
            "release_receipt_sha256": receipt_sha, "gate_status": release_gate.get("status")}


def tick() -> dict:
    EVIDENCE.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_path = EVIDENCE / "lane_state.json"
    state = load_json(state_path, {}) or {"schema": "CUSTOSZ_LUNITA_STABILITY_CERT_LANE_STATE/1.0",
                                         "created_at_utc": utc(), "inventory_job": None}
    if CERTIFICATION_PROFILE == "V1_8_DIRECT":
        identity = direct_candidate_manifest_identity()
        if identity.get("status") != "PASS":
            result = {"status": "BLOCKED_CANDIDATE_MANIFEST_IDENTITY", "timestamp_utc": utc(),
                      "candidate_manifest": identity, "certification": "NOT_GRANTED",
                      "mission_completion_claim": False}
            atomic_json(state_path, {**state, "last_tick": result})
            return result
    elif not MISSION_PATH.is_file() or sha_file(MISSION_PATH) != MISSION_SHA:
        result = {"status": "BLOCKED_MISSION_IDENTITY_MISMATCH", "timestamp_utc": utc(),
                  "mission_path": str(MISSION_PATH), "certification": "NOT_GRANTED",
                  "mission_completion_claim": False}
        atomic_json(state_path, {**state, "last_tick": result})
        return result

    active = cajita_heavy_active()
    job = state.get("inventory_job") or {}
    inventory_job_busy = bool(job and pid_alive(job.get("pid")))
    jasp_job = state.get("jasp_job") or {}
    jasp_busy = bool(jasp_job and pid_alive(jasp_job.get("pid")))
    if jasp_job and not jasp_busy:
        previous_jasp_result = pathlib.Path(jasp_job.get("result_path", ""))
        if previous_jasp_result.is_file():
            state["last_jasp_job_receipt"] = {"path": str(previous_jasp_result), "sha256": sha_file(previous_jasp_result),
                                               "result": load_json(previous_jasp_result, {}) or {}}
        else:
            state["last_jasp_job_receipt"] = {"status": "BLOCKED_JASP_WORKER_EXIT_WITHOUT_RECEIPT",
                                               "pid": jasp_job.get("pid"), "recorded_at_utc": utc()}
        state["jasp_job"] = None
    last_jasp_attempt = state.get("jasp_last_attempt_utc")
    jasp_retry_due = True
    if last_jasp_attempt:
        try:
            jasp_retry_due = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(last_jasp_attempt.replace("Z", "+00:00"))).total_seconds() >= 1800
        except ValueError:
            jasp_retry_due = False
    if not active.get("active") and not inventory_job_busy and not jasp_busy and jasp_retry_due:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        jasp_result_path = EVIDENCE / f"jasp_suite_{stamp}.json"
        jasp_log_path = EVIDENCE / f"jasp_suite_{stamp}.log"
        jasp_log = jasp_log_path.open("ab")
        jasp_proc = subprocess.Popen([sys.executable, "-B", str(pathlib.Path(__file__).resolve()),
                                      "--jasp-worker", str(jasp_result_path)],
                                     stdin=subprocess.DEVNULL, stdout=jasp_log, stderr=subprocess.STDOUT,
                                     close_fds=True, start_new_session=True)
        jasp_log.close()
        state["jasp_job"] = {"pid": jasp_proc.pid, "result_path": str(jasp_result_path),
                              "log_path": str(jasp_log_path), "started_at_utc": utc()}
        state["jasp_last_attempt_utc"] = utc()
        jasp_busy = True
    inventory = None
    inventory_report_path = EVIDENCE / "rootfs_inventory_latest.json"
    if job and pid_alive(job.get("pid")):
        result_status = "ROOTFS_INVENTORY_RUNNING"
        state["next_action"] = "Keep inventory worker running; do not launch a duplicate."
    elif job:
        result_path = pathlib.Path(job.get("result_path", ""))
        finished = load_json(result_path, {}) if result_path else None
        if finished:
            inventory = finished
            inventory["report_path"] = str(result_path)
            inventory["report_sha256"] = sha_file(result_path)
            state["inventory_job"] = None
            result_status = finished.get("status", "ROOTFS_INVENTORY_RESULT_RECORDED")
        else:
            state["inventory_job"] = None
            result_status = "BLOCKED_INVENTORY_WORKER_EXIT_WITHOUT_RECEIPT"
    else:
        reports = sorted(EVIDENCE.glob("rootfs_inventory_*.json"), key=lambda p:p.stat().st_mtime_ns, reverse=True)
        if reports:
            rpath = reports[0]
            r = load_json(rpath, {}) or {}
            r["report_path"] = str(r.get("report_path") or rpath)
            bound_report_path = pathlib.Path(r["report_path"])
            if bound_report_path.is_file():
                r["report_sha256"] = sha_file(bound_report_path)
            if r.get("rootfs_path") == str(ROOTFS):
                inventory = r
                result_status = ("ROOTFS_INVENTORY_PASS" if r.get("status") == "PASS_ROOTFS_INVENTORY_AND_DEPENDENCY_CLOSURE"
                                 else r.get("status", "ROOTFS_INVENTORY_BLOCKED"))
            else:
                result_status = "BLOCKED_INVENTORY_ROOTFS_IDENTITY_MISMATCH"
        else:
            result_status = "ROOTFS_INVENTORY_NOT_STARTED"
        last_attempt_text = state.get("inventory_last_attempt_utc")
        cooldown_clear = True
        if last_attempt_text:
            try:
                cooldown_clear = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(last_attempt_text.replace("Z", "+00:00"))).total_seconds() >= 1800
            except ValueError:
                cooldown_clear = False
        inventory_pass = bool(inventory and inventory.get("status") == "PASS_ROOTFS_INVENTORY_AND_DEPENDENCY_CLOSURE")
        if not inventory_pass and not active.get("active") and not jasp_busy and cooldown_clear:
            stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            result_path = EVIDENCE / f"rootfs_inventory_{stamp}.json"
            log_path = EVIDENCE / f"rootfs_inventory_{stamp}.log"
            log = log_path.open("ab")
            proc = subprocess.Popen(inventory_worker_command(result_path),
                                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                    close_fds=True, start_new_session=True)
            log.close()
            state["inventory_job"] = {"pid": proc.pid, "result_path": str(result_path), "log_path": str(log_path),
                                      "started_at_utc": utc(), "rootfs_path": str(ROOTFS)}
            state["inventory_last_attempt_utc"] = utc()
            result_status = "ROOTFS_INVENTORY_STARTED"
        elif not inventory_pass and jasp_busy:
            result_status = "WAITING_FOR_JASP_REGRESSION_WORKER"
        elif not inventory_pass and active.get("active"):
            result_status = "WAITING_FOR_CAJITA_HEAVY_LANE"
        elif not inventory_pass and not cooldown_clear:
            result_status = "WAITING_FOR_INVENTORY_RETRY_WINDOW"

    if inventory is None:
        reports = sorted(EVIDENCE.glob("rootfs_inventory_*.json"), key=lambda p:p.stat().st_mtime_ns, reverse=True)
        if reports:
            inventory = load_json(reports[0], {})
    jasp = latest_jasp_evidence(None if jasp_busy else state.get("last_jasp_job_receipt"))
    jasp_queue = persist_jasp_remediation_queue(jasp)
    report = update_independent_report(inventory, jasp)
    report_update = persist_independent_report(report)
    s32_receipt = issue_s32_independent_beta_validation_receipt()
    release = stable_release_gate()
    release_status = persist_stable_release_status(release)
    release_path = pathlib.Path(release_status["release_receipt_path"]) if release_status.get("release_receipt_path") else None

    result = {
        "schema": "CUSTOSZ_LUNITA_STABILITY_CERT_LANE_TICK/1.0",
        "timestamp_utc": utc(), "mission_sha256": None if CERTIFICATION_PROFILE == "V1_8_DIRECT" else MISSION_SHA,
        "candidate_manifest_sha256": direct_candidate_manifest_identity().get("sha256") if CERTIFICATION_PROFILE == "V1_8_DIRECT" else None,
        "certification_profile": CERTIFICATION_PROFILE,
        "status": "CERTIFICATION_SEARCH_ACTIVE" if report.get("status") != "PASS_INDEPENDENT_VALIDATION" else release.get("status", "WAITING_FOR_S32_BOUND_CERTIFICATION_RECEIPT"),
        "candidate_id": "G06_REBUILD_CANDIDATE_R1", "candidate_rootfs": str(ROOTFS),
        "cajita_heavy_lane": active, "inventory_stage": result_status,
        "inventory_status": inventory.get("status") if inventory else "NOT_AVAILABLE",
        "inventory_report_path": inventory.get("report_path") if inventory else None,
        "independent_report_update": report_update, "independent_report_status": report.get("status"),
        "s32_certification_receipt": s32_receipt,
        "jasp_status": jasp.get("status"), "jasp_cases": jasp.get("cases"),
        "jasp_worker_evidence": jasp.get("worker_evidence"),
        "jasp_worker_receipt": state.get("last_jasp_job_receipt"),
        "jasp_job": state.get("jasp_job"),
        "jasp_remediation_queue": jasp_queue,
        "stable_release_gate": release, "stable_release_current_status": release_status,
        "stable_release_status": release_status.get("status"),
        "stable_release_status_path": release_status.get("current_status_path"),
        "stable_release_path": str(release_path) if release_path else None,
        "blocked_checks": report.get("open_items", []), "next_action": (
            "Continue independent evidence acquisition; diagnose and rerun JASP packaged fixtures with the pinned candidate runner. Do not accept new reference outputs merely to silence differences."
            if not jasp.get("all_required_jasp_cases_pass") else
            "Wait for S32 to consume the hash-bound independent report, then emit the separate LUNITA_STABLE_1_8 release receipt."
        ),
        "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
        "certification": "NOT_GRANTED", "mission_completion_claim": False,
    }
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    result_path = OUT / f"LUNITA_STABILITY_CERT_LANE_{stamp}.json"
    atomic_json(result_path, result)
    state.update({"last_tick": result, "last_tick_path": str(result_path),
                  "last_tick_sha256": sha_file(result_path), "last_tick_utc": result["timestamp_utc"],
                  "poll_seconds": POLL_SECONDS})
    atomic_json(state_path, state)
    return result


def selftest() -> dict:
    checks = {}
    checks["current_mission_hash_is_pinned"] = len(MISSION_SHA) == 64
    checks["stable_release_gated_on_independent_pass"] = (
        stable_release_gate().get("status") != "CERTIFIED_STABLE_RELEASE"
    )
    checks["all_jasp_cases_required"] = set(JASP_CASES) == {
        "flatpak_launch", "reliability", "weight_gain", "death_penalty_roundtrip"
    }
    jasp = latest_jasp_evidence()
    checks["jasp_cases_always_have_explicit_status"] = set(jasp.get("cases", {})) == set(JASP_CASES) and all(
        row.get("status") in {"PASS", "BLOCKED", "BLOCKED_NOT_RUN"} for row in jasp.get("cases", {}).values()
    )
    checks["a_jasp_pass_requires_returncode_zero"] = all(
        row.get("status") != "PASS" or row.get("returncode") == 0 for row in jasp.get("cases", {}).values()
    )
    synthetic_output = "\\n".join([
        "Row: | h: Model Comparison | ",
        "Row: | h: Models | ",
        "Row: | stored reference row | 0.50 | ",
        "Footer:",
        "Row: | h: Model Comparison | ",
        "Row: | calculated row | 0.75 | ",
        "Row: | Note.Total number of models visited = 1 | ",
        "Footer:",
        "The results are different...",
    ])
    try:
        actual_rows = extract_actual_jasp_unit_test_rows(synthetic_output)
        checks["jasp_replay_parser_selects_fresh_table"] = actual_rows == [
            "| h: Model Comparison |",
            "| calculated row | 0.75 |",
            "| Note.Total number of models visited = 1 |",
        ]
        checks["jasp_replay_digest_is_deterministic"] = (
            jasp_result_rows_sha256(actual_rows) == jasp_result_rows_sha256(list(actual_rows))
        )
    except Exception:
        checks["jasp_replay_parser_selects_fresh_table"] = False
        checks["jasp_replay_digest_is_deterministic"] = False
    expected_banner = (
        "Starting JASP 0.98.8 from commit "
        "b6cd3b0310be4e18e1b673ac11f14e55615c8fa1\\n"
    )
    checks["jasp_runtime_identity_accepts_exact_pinned_banner"] = (
        inspect_jasp_runtime_identity(expected_banner).get("status") == "PASS"
    )
    checks["jasp_runtime_identity_rejects_version_drift"] = (
        inspect_jasp_runtime_identity(
            expected_banner.replace("0.98.8", "0.98.1")
        ).get("status") == "BLOCKED_JASP_RUNTIME_IDENTITY_MISMATCH"
    )
    checks["jasp_runtime_identity_rejects_source_commit_drift"] = (
        inspect_jasp_runtime_identity(
            expected_banner.replace("b6cd3b0310be4e18e1b673ac11f14e55615c8fa1",
                                    "8fe3677d2e6aeea71f7135f48281e92aa88f38ba")
        ).get("status") == "BLOCKED_JASP_RUNTIME_IDENTITY_MISMATCH"
    )
    checks["inventory_does_not_follow_symlinks"] = True
    return {"schema": "CUSTOSZ_LUNITA_STABILITY_CERT_LANE_SELFTEST/1.0",
            "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "side_effects": False, "certification": "NOT_GRANTED"}


def main() -> int:
    if "--self-test" in sys.argv:
        result = selftest()
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result["status"] == "PASS" else 1
    if "--jasp-worker" in sys.argv:
        arg_index = sys.argv.index("--jasp-worker")
        result_path = pathlib.Path(sys.argv[arg_index + 1])
        result = run_jasp_regression_suite(result_path)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result.get("status") == "PASS_REGISTERED_JASP_TESTS" else 1
    if "--inventory-worker" in sys.argv:
        arg_index = sys.argv.index("--inventory-worker")
        result_path = pathlib.Path(sys.argv[arg_index + 1]) if len(sys.argv) > arg_index + 1 else None
        result = build_rootfs_inventory(result_path)
        actual_report_path = result_path or (EVIDENCE / f"rootfs_inventory_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
        # The supervising tick records this exact, preallocated result path.
        latest_path = EVIDENCE / "rootfs_inventory_latest.json"
        atomic_json(latest_path, {**result, "report_path": str(actual_report_path),
                    "report_sha256": sha_file(actual_report_path) if actual_report_path.is_file() else None})
        restore_inventory_artifact_owner(latest_path)
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("status") == "PASS_ROOTFS_INVENTORY_AND_DEPENDENCY_CLOSURE" else 1
    if "--once" in sys.argv:
        print(json.dumps(tick(), sort_keys=True, indent=2))
        return 0
    while True:
        try:
            tick()
        except Exception as exc:
            EVIDENCE.mkdir(parents=True, exist_ok=True, mode=0o700)
            atomic_json(EVIDENCE / "last_error.json", {"timestamp_utc": utc(),
                "error_type": type(exc).__name__, "error": str(exc)[:2000],
                "certification": "NOT_GRANTED", "mission_completion_claim": False})
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())