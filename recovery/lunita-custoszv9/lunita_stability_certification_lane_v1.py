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
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import uuid

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
    """Run /app/bin/JASP. org.jaspstats.JASP is a shell wrapper that forwards only $1,
    so --unitTest never receives the fixture path and JASP prints help."""
    return [
        "/usr/bin/flatpak", "--system", "run", "--unshare=network",
        "--command=/app/bin/JASP",
        "--socket=x11",
        "--env=DISPLAY=:99",
        "--env=QT_QPA_PLATFORM=xcb",
        "--env=LIBGL_ALWAYS_SOFTWARE=1",
        "--env=QTWEBENGINE_DISABLE_SANDBOX=1",
        "--env=QML2_IMPORT_PATH=/app/qml",
        *flatpak_options, "org.jaspstats.JASP", *app_args,
    ]


def jasp_process_env(base: dict[str, str]) -> dict[str, str]:
    env = dict(base)
    # The GitHub runner injects a host Python library path. It must not leak
    # into the Flatpak sandbox ahead of the KDE runtime.
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("LD_PRELOAD", None)
    env["QT_QPA_PLATFORM"] = "offscreen"
    return env


def run_death_penalty_roundtrip(actual_commit: str, env: dict[str, str], stamp: str) -> dict:
    """Run the strict JASP save-and-rerun test on a temporary copy, not the packaged source."""
    source = ROOTFS / "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp"
    report_path = OUT / f"JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_{stamp}.json"
    base = {"schema": "CUSTOSZ_LUNITA_JASP_UNITTEST_ROUNDTRIP/1.0",
            "captured_at_utc": utc(), "app_commit": actual_commit,
            "app_id": "org.jaspstats.JASP", "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "beta_revision": "beta-v1.7", "network_unshared": True, "flatpak_sandbox": True,
            "real_analysis_engine_invoked": "JASPEngine", "sample_relative_path": "Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp",
            "downloads_performed": False, "persistent_sample_copy_created": False,
            "certification": "NOT_GRANTED", "mission_completion_claim": False}
    if not source.is_file():
        result = {**base, "status": "BLOCKED_PACKAGED_ROUNDTRIP_FIXTURE_MISSING",
                  "original_sample_unchanged": False, "strict_rerun_after_save": {"status": "BLOCKED", "returncode": 125},
                  "source_fixture_path": str(source)}
        atomic_json(report_path, result)
        return result
    expected_original_sha = "fc8b6f8faf0e4437c8e4ab4bd922b3e959a0d4549c813b229bc5708050851895"
    original_before = sha_file(source)
    save_run = {"status": "BLOCKED", "returncode": 125}
    rerun = {"status": "BLOCKED", "returncode": 125}
    temp_before = None
    temp_after = None
    temp_after_rerun = None
    temp_fixture = None
    temp_root = None
    try:
        with __import__("tempfile").TemporaryDirectory(prefix="lunita-jasp-death-roundtrip-") as tmp:
            temp_root = pathlib.Path(tmp)
            temp_fixture = temp_root / "DeathPenalty.jasp"
            shutil.copy2(source, temp_fixture)
            temp_before = sha_file(temp_fixture)
            cmd = flatpak_jasp_launch([f"--filesystem={temp_root}"], ["--unitTest", str(temp_fixture)])
            save_log_path = OUT / f"JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_{stamp}_save.log"
            rerun_log_path = OUT / f"JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_{stamp}_rerun.log"
            save_started = utc()
            try:
                save_proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           text=True, timeout=300, check=False)
                save_rc = int(save_proc.returncode)
                save_log_path.write_text(f"START_UTC={save_started}\nCOMMAND={json.dumps(cmd)}\nAPP_COMMIT={actual_commit}\n"
                                         + save_proc.stdout + ("" if save_proc.stdout.endswith("\n") else "\n")
                                         + f"SAVE_RUN_RC={save_rc}\nFINISHED_UTC={utc()}\n",
                                         encoding="utf-8", errors="replace")
                save_run = {"status": "PASS" if save_rc == 0 else "FAIL", "returncode": save_rc,
                            "log_path": str(save_log_path), "log_sha256": sha_file(save_log_path)}
            except subprocess.TimeoutExpired as exc:
                output = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                save_log_path.write_text(f"START_UTC={save_started}\nCOMMAND={json.dumps(cmd)}\n{output}\nSAVE_RUN_RC=124\nTIMEOUT=300\n",
                                         encoding="utf-8", errors="replace")
                save_run = {"status": "BLOCKED_TIMEOUT", "returncode": 124,
                            "log_path": str(save_log_path), "log_sha256": sha_file(save_log_path)}
            temp_after = sha_file(temp_fixture) if temp_fixture.is_file() else None
            rerun_started = utc()
            try:
                rerun_proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            text=True, timeout=300, check=False)
                rerun_rc = int(rerun_proc.returncode)
                rerun_log_path.write_text(f"START_UTC={rerun_started}\nCOMMAND={json.dumps(cmd)}\nAPP_COMMIT={actual_commit}\n"
                                          + rerun_proc.stdout + ("" if rerun_proc.stdout.endswith("\n") else "\n")
                                          + f"STRICT_RERUN_RC={rerun_rc}\nFINISHED_UTC={utc()}\n",
                                          encoding="utf-8", errors="replace")
                rerun = {"status": "PASS" if rerun_rc == 0 else "FAIL", "returncode": rerun_rc,
                         "log_path": str(rerun_log_path), "log_sha256": sha_file(rerun_log_path)}
            except subprocess.TimeoutExpired as exc:
                output = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                rerun_log_path.write_text(f"START_UTC={rerun_started}\nCOMMAND={json.dumps(cmd)}\n{output}\nSTRICT_RERUN_RC=124\nTIMEOUT=300\n",
                                          encoding="utf-8", errors="replace")
                rerun = {"status": "BLOCKED_TIMEOUT", "returncode": 124,
                         "log_path": str(rerun_log_path), "log_sha256": sha_file(rerun_log_path)}
            temp_after_rerun = sha_file(temp_fixture) if temp_fixture.is_file() else None
    except Exception as exc:
        base["executor_error"] = {"type": type(exc).__name__, "message": str(exc)[:1200]}
    original_after = sha_file(source) if source.is_file() else None
    unchanged = bool(original_before == expected_original_sha and original_after == expected_original_sha)
    roundtrip_reproducible = bool(temp_before == expected_original_sha and temp_after and temp_after == temp_after_rerun and temp_root and not temp_root.exists())
    final_status = "PASS" if save_run.get("returncode") == 0 and rerun.get("returncode") == 0 and unchanged and roundtrip_reproducible else "FAIL"
    result = {**base, "captured_at_utc": utc(), "status": "PASS_JASP_STRICT_ROUNDTRIP" if final_status == "PASS" else "BLOCKED_JASP_STRICT_ROUNDTRIP",
              "expected_original_sample_sha256": expected_original_sha,
              "original_sample_sha256_before": original_before, "original_sample_sha256_after": original_after,
              "original_sample_identity_matches_pin": original_before == expected_original_sha,
              "original_sample_unchanged": unchanged, "source_fixture_path": str(source),
              "save_run": save_run,
              "strict_rerun_after_save": {**rerun, "status": final_status},
              "temporary_fixture_sha256_before": temp_before, "temporary_fixture_sha256_after_save": temp_after,
              "temporary_fixture_sha256_after_rerun": temp_after_rerun,
              "temporary_fixture_changed": bool(temp_before and temp_after and temp_before != temp_after),
              "temporary_fixture_path": str(temp_fixture) if temp_fixture else None,
              "temporary_fixture_removed_after_test": bool(temp_root and not temp_root.exists()),
              "downloaded": False}
    atomic_json(report_path, result)
    result["report_path"] = str(report_path)
    result["report_sha256"] = sha_file(report_path)
    return result


def run_jasp_regression_suite(result_path: pathlib.Path) -> dict:
    """Rerun the registered JASP packaged-data unit tests in the pinned sandbox."""
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT.mkdir(parents=True, exist_ok=True)
    expected_commit = "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"
    fixtures = {
        "flatpak_launch": ("JASP_UNITTEST_FLATPAK", "/app/lunita-fixtures/DeathPenalty.jasp", "JASP_UNITTEST_RC"),
        "reliability": ("JASP_UNITTEST_RELIABILITY", "/app/lunita-fixtures/Reliability.jasp", "JASP_RELIABILITY_UNITTEST_RC"),
        "weight_gain": ("JASP_UNITTEST_WEIGHT_GAIN", "/app/lunita-fixtures/WeightGain.jasp", "JASP_WEIGHT_GAIN_UNITTEST_RC"),
    }
    env = jasp_process_env(os.environ)
    env["FLATPAK_SYSTEM_DIR"] = str(ROOTFS / "var/lib/flatpak")
    results = {"schema": "CUSTOSZ_LUNITA_JASP_AUTOMATED_REGRESSION_SUITE/1.0", "timestamp_utc": utc(),
               "candidate_id": "G06_REBUILD_CANDIDATE_R1", "expected_app_commit": expected_commit,
               "flatpak_system_dir": env["FLATPAK_SYSTEM_DIR"], "network_unshared": True,
               "tests": {}, "certification": "NOT_GRANTED", "mission_completion_claim": False}
    try:
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
            for case_id, (prefix, fixture, marker) in fixtures.items():
                log_path = OUT / f"{prefix}_{stamp}.log"
                started = utc()
                header = (f"START_UTC={started}\nAPP_COMMIT={actual_commit}\nTEST_FILE={fixture}\n"
                          "EXECUTION_MODE=PINNED_CANDIDATE_FLATPAK_SANDBOX_NETWORK_UNSHARED\n")
                try:
                    run = subprocess.run(flatpak_jasp_launch([], ["--unitTest", fixture]),
                                         env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, timeout=300, check=False)
                    rc = int(run.returncode)
                    payload = header + run.stdout + ("\n" if not run.stdout.endswith("\n") else "") + f"\n{marker}={rc}\nFINISHED_UTC={utc()}\n"
                    log_path.write_text(payload, encoding="utf-8", errors="replace")
                    results["tests"][case_id] = {"status": "PASS" if rc == 0 else "BLOCKED", "returncode": rc,
                        "fixture": fixture, "log_path": str(log_path), "log_sha256": sha_file(log_path),
                        "command": flatpak_jasp_launch([], ["--unitTest", fixture]),
                        "started_at_utc": started, "finished_at_utc": utc()}
                except subprocess.TimeoutExpired as exc:
                    out = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                    log_path.write_text(header + out + f"\n{marker}=124\nTIMEOUT=300\n", encoding="utf-8")
                    results["tests"][case_id] = {"status": "BLOCKED_TIMEOUT", "returncode": 124,
                        "fixture": fixture, "log_path": str(log_path), "log_sha256": sha_file(log_path)}
                except Exception as exc:
                    log_path.write_text(header + f"EXECUTION_ERROR={type(exc).__name__}:{str(exc)[:1000]}\n{marker}=125\n", encoding="utf-8")
                    results["tests"][case_id] = {"status": "BLOCKED_EXECUTION_ERROR", "returncode": 125,
                        "fixture": fixture, "log_path": str(log_path), "log_sha256": sha_file(log_path)}
            results["roundtrip_gate"] = run_death_penalty_roundtrip(actual_commit, env, stamp)
    except Exception as exc:
        results["status"] = "BLOCKED_JASP_TEST_EXECUTOR"
        results["executor_error"] = {"type": type(exc).__name__, "message": str(exc)[:1200]}
        atomic_json(result_path, results)
        return results
    roundtrip = results.get("roundtrip_gate") or {"status": "BLOCKED_ROUNDTRIP_NOT_RUN"}
    roundtrip_ok = (roundtrip.get("status") == "PASS_JASP_STRICT_ROUNDTRIP"
                    and (roundtrip.get("strict_rerun_after_save") or {}).get("returncode") == 0
                    and roundtrip.get("original_sample_unchanged") is True)
    results["status"] = "PASS_REGISTERED_JASP_TESTS" if (
        results["tests"] and all(x.get("status") == "PASS" and x.get("returncode") == 0
                                 for x in results["tests"].values()) and roundtrip_ok
    ) else "BLOCKED_JASP_REGRESSION"
    results["roundtrip_gate"] = roundtrip
    atomic_json(result_path, results)
    return results


INVENTORY_PRIVILEGED_ENV = (
    "LUNITA_ROOTFS",
    "LUNITA_STATE_DIR",
    "LUNITA_OUTPUT_DIR",
    "LUNITA_EVIDENCE_DIR",
    "LUNITA_CANDIDATE_DIR",
    "LUNITA_TARGET_RUNTIME_RECEIPT_DIR",
    "LUNITA_CANDIDATE_MANIFEST",
    "LUNITA_CERTIFICATION_PROFILE",
)


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


def latest_jasp_evidence() -> dict:
    rows = {}
    for case, (prefix, pattern, marker) in JASP_CASES.items():
        files = sorted((OUT.glob(prefix + pattern)), key=lambda p: p.stat().st_mtime_ns, reverse=True)
        if not files:
            rows[case] = {"status": "BLOCKED_NOT_RUN", "returncode": None, "evidence_path": None}
            continue
        p = files[0]
        item = {"evidence_path": str(p), "evidence_sha256": sha_file(p),
                "mtime_ns": p.stat().st_mtime_ns, "status": "BLOCKED", "returncode": None}
        if p.suffix == ".json":
            data = load_json(p, {}) or {}
            rerun = data.get("strict_rerun_after_save") or {}
            save_run = data.get("save_run") or {}
            rc = rerun.get("returncode")
            temp_before = data.get("temporary_fixture_sha256_before")
            temp_after_save = data.get("temporary_fixture_sha256_after_save")
            temp_after_rerun = data.get("temporary_fixture_sha256_after_rerun")
            passed = (
                data.get("schema") == "CUSTOSZ_LUNITA_JASP_UNITTEST_ROUNDTRIP/1.0"
                and data.get("app_commit") == "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"
                and data.get("network_unshared") is True and data.get("flatpak_sandbox") is True
                and data.get("status") == "PASS_JASP_STRICT_ROUNDTRIP"
                and rerun.get("status") == "PASS" and rc == 0
                and save_run.get("returncode") == 0
                and data.get("original_sample_identity_matches_pin") is True
                and data.get("original_sample_unchanged") is True
                and data.get("temporary_fixture_removed_after_test") is True
                and bool(temp_before) and temp_before == data.get("expected_original_sample_sha256")
                and bool(temp_after_save) and temp_after_save == temp_after_rerun
            )
            item.update({"returncode": rc, "save_returncode": save_run.get("returncode"),
                         "status": "PASS" if passed else "BLOCKED",
                         "case_status": data.get("status"), "rerun_status": rerun.get("status"),
                         "original_sample_unchanged": data.get("original_sample_unchanged"),
                         "original_sample_identity_matches_pin": data.get("original_sample_identity_matches_pin"),
                         "temporary_fixture_removed_after_test": data.get("temporary_fixture_removed_after_test"),
                         "temporary_fixture_stable_after_save_and_rerun": bool(temp_after_save and temp_after_save == temp_after_rerun)})
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
            passed = rc == 0 and pinned_commit and sandbox_bound
            item.update({"returncode": rc, "status": "PASS" if passed else "BLOCKED",
                         "observed_app_commits": commits, "pinned_commit_match": pinned_commit,
                         "sandbox_execution_marker_present": sandbox_bound,
                         "semantic_shape_mismatch": bool(re.search(r"Row is missing|Total number of models visited\s*=\s*\d+\s*!=|results are different", text, re.I)),
                         "log_has_numeric_deltas": bool(re.search(r"\d+(?:\.\d+)?\s*!=\s*\d+(?:\.\d+)?", text))})
        rows[case] = item
    all_pass = all(x.get("status") == "PASS" and x.get("returncode") == 0 for x in rows.values())
    return {"status": "PASS_JASP_PACKAGED_FIXTURE_NONREGRESSION" if all_pass else "BLOCKED_JASP_PACKAGED_FIXTURE_NONREGRESSION",
            "all_required_jasp_cases_pass": all_pass, "cases": rows,
            "next_action": "Use the pinned candidate JASP runner on isolated fixture copies; diagnose model-count/result differences and precision deltas separately. Do not rewrite reference fixtures or relax thresholds to force a pass."}


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
            "flatpak_launch": "Verify pinned JASP startup/runner and capture an exact successful return code.",
            "reliability": "Diagnose full-precision output differences versus packaged reference; distinguish harmless display formatting from semantic/statistical deltas with a documented independent tolerance policy.",
            "weight_gain": "Diagnose numeric display/precision deltas against the packaged reference without mutating the original fixture.",
            "death_penalty_roundtrip": "Diagnose changed model count and posterior/BF values on an isolated fixture copy; preserve original bytes and determine whether the candidate build has a genuine non-regression issue.",
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
    jasp_case_evidence_valid = (set(jasp_cases) == set(JASP_CASES) and all(
        row.get("status") == "PASS" and row.get("returncode") == 0
        and pathlib.Path(row.get("evidence_path", "")).is_file()
        and sha_file(pathlib.Path(row.get("evidence_path", ""))) == row.get("evidence_sha256")
        for row in jasp_cases.values()
    ))
    jasp_pass = jasp.get("status") == "PASS_JASP_PACKAGED_FIXTURE_NONREGRESSION" and jasp_case_evidence_valid
    checks["jasp_packaged_fixture_nonregression"] = {
        "status": "PASS" if jasp_pass else "BLOCKED",
        "returncode": 0 if jasp_pass else 1,
        "cases": jasp_cases, "next_action": jasp.get("next_action"),
        "all_case_evidence_hashes_current": jasp_case_evidence_valid,
        "evidence": {row["evidence_path"]: row["evidence_sha256"] for row in jasp_cases.values()
                     if row.get("evidence_path") and row.get("evidence_sha256")},
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
        "squashfs_image_and_package_binding",
    }
    if not isinstance(checks, dict) or not required_checks.issubset(checks):
        return {"status": "BLOCKED_REQUIRED_INDEPENDENT_CHECKS_MISSING", "certification": "NOT_GRANTED"}
    if any(not _stable_check(check) for check in checks.values()):
        return {"status": "BLOCKED_REQUIRED_INDEPENDENT_CHECKS", "certification": "NOT_GRANTED"}
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
    jasp = latest_jasp_evidence()
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
