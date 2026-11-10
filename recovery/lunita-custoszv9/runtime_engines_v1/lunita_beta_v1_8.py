#!/usr/bin/env python3
"""Lunita beta v1.8 additive command wrapper.

Legacy commands are delegated unchanged to the hash-pinned beta v1.7 launcher.
New engine operations are exposed through the command-team-bound E01-E15 gateway.
This file does not replace or rewrite the v1.7 launcher.
"""
from __future__ import annotations

import hashlib
import json
import fcntl
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone
from typing import Sequence

ROOT = pathlib.Path(os.environ.get("LUNITA_ROOT", "/opt/lunita")).expanduser()
OVERLAY = ROOT / "engines/runtime_engines_v1"
LEGACY_LAUNCHER = ROOT / "agent/lunita.py"
LEGACY_SHA256 = "46efd711729c344e7efba9ce2503127c48f0b88207cc5a17311ff1d555b075b2"
LEGACY_COMMANDS = {
    "start", "qwen-load", "qwen-inference", "brujula-self-test",
    "r-self-test", "jamovi-self-test", "jasp-self-test", "fault",
}


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    site = OVERLAY / "vendor/python3.12/site-packages"
    paths = [str(site), str(OVERLAY)]
    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(paths)
    env.setdefault("LUNITA_FASTEMBED_CACHE", str(OVERLAY / "model-cache/fastembed"))
    env.setdefault("LUNITA_VECTOR_DB_PATH", "/var/lib/lunita/vectors")
    env.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("TRANSFORMERS_OFFLINE", "1")
    return env


def run_legacy(arguments: Sequence[str]) -> int:
    if not LEGACY_LAUNCHER.is_file():
        print("DENIED: the preserved beta v1.7 launcher is missing", file=sys.stderr)
        return 2
    observed = sha256_file(LEGACY_LAUNCHER)
    if observed != LEGACY_SHA256:
        print("DENIED: beta v1.7 launcher SHA-256 mismatch", file=sys.stderr)
        return 3
    # Preserve the legacy v1.7 Python environment exactly. The target-side
    # acceptance process itself runs with the v1.8 overlay on PYTHONPATH; remove
    # only those two overlay entries before delegating to v1.7.
    environment = os.environ.copy()
    overlay_entries = {
        str(OVERLAY.resolve()),
        str((OVERLAY / "vendor/python3.12/site-packages").resolve()),
    }
    existing = environment.get("PYTHONPATH", "")
    retained = []
    for entry in existing.split(os.pathsep):
        if not entry:
            continue
        try:
            normalized = str(pathlib.Path(entry).resolve())
        except (OSError, RuntimeError):
            normalized = entry
        if normalized not in overlay_entries:
            retained.append(entry)
    if retained:
        environment["PYTHONPATH"] = os.pathsep.join(retained)
    else:
        environment.pop("PYTHONPATH", None)
    target_rootfs_value = environment.get("LUNITA_TARGET_ROOTFS")
    if target_rootfs_value:
        try:
            target_rootfs = pathlib.Path(target_rootfs_value).resolve(strict=True)
            launcher_relative = LEGACY_LAUNCHER.resolve(strict=True).relative_to(target_rootfs)
        except (OSError, ValueError) as exc:
            print(f"DENIED: legacy launcher is not inside the declared target rootfs: {exc}", file=sys.stderr)
            return 5
        guest_launcher = "/" + launcher_relative.as_posix()
        guest_environment = [
            "HOME=/home/lunita",
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "XDG_CACHE_HOME=/tmp/lunita-xdg/cache",
            "XDG_CONFIG_HOME=/tmp/lunita-xdg/config",
            "XDG_DATA_HOME=/tmp/lunita-xdg/data",
            "XDG_RUNTIME_DIR=/run/lunita-runtime-1000",
            "FLATPAK_SYSTEM_DIR=/var/lib/flatpak",
            "R_HOME=/opt/lunita/instruments/lapiz/R-4.6.1/lib/R",
        ]
        command = [
            "sudo", "-n", "chroot", "--userspec=1000:1000",
            str(target_rootfs), "/usr/bin/env", "-C", "/tmp",
            *guest_environment, "/usr/bin/python3.12", guest_launcher, *arguments,
        ]
        child_environment = os.environ.copy()
        child_environment.pop("PYTHONPATH", None)
    else:
        command = [sys.executable, str(LEGACY_LAUNCHER), *arguments]
        child_environment = environment
    try:
        return subprocess.run(command, env=child_environment, check=False).returncode
    except OSError as exc:
        print(f"DENIED: unable to delegate to beta v1.7: {exc}", file=sys.stderr)
        return 4


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def append_execution_audit(request: dict, result: dict) -> dict:
    """Append one digest-only execution event; refuse malformed/tampered history."""
    import engine_runtime_v1 as engine
    path = pathlib.Path(os.environ.get(
        "LUNITA_ENGINE_AUDIT_LOG", "/var/lib/lunita/audit/engine-execution.jsonl"
    ))
    absolute = pathlib.Path(os.path.abspath(path))
    current = pathlib.Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current = current / component
        if current.exists() and current.is_symlink():
            raise RuntimeError(f"Audit log path contains a symlink: {current}")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR | os.O_APPEND
    fd = os.open(path, flags, 0o600)
    try:
        if not os.path.isfile(path) or os.path.islink(path):
            raise RuntimeError("Audit log is not a regular non-symlink file")
        fcntl.flock(fd, fcntl.LOCK_EX)
        with os.fdopen(os.dup(fd), "r", encoding="utf-8") as stream:
            lines = stream.read().splitlines()
        records = []
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                raise RuntimeError(f"Blank line in append-only audit log at line {line_number}")
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Malformed audit record at line {line_number}") from exc
        verified = engine.verify_provenance_chain(records)
        if verified["status"] != "PASS_PROVENANCE_CHAIN":
            raise RuntimeError("Existing audit chain failed integrity verification")
        event = {
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "command": request["command"],
            "agent": request["agent"],
            "engine_id": request["engine_id"],
            "request_sha256": _canonical_sha256(request),
            "result_sha256": _canonical_sha256(result),
            "result_status": result["status"],
        }
        record = engine.append_provenance_event(verified["terminal_hash"], event)
        encoded = (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        view = memoryview(encoded)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("Short write while appending audit record")
            view = view[written:]
        os.fsync(fd)
        return record
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def engine_status() -> dict:
    import engine_runtime_v1 as engine
    return {
        "schema": "LUNITA_BETA_V1_8_ENGINE_STATUS/1.0",
        "status": "RUNTIME_CANDIDATE",
        "engine_registry": engine.validate_registry(),
        "instrument_registry": {key: dict(value) for key, value in engine.INSTRUMENT_REGISTRY.items()},
        "dependencies": engine.engine_dependency_inventory(),
        "command_agents": {key: list(value) for key, value in engine.COMMAND_AGENTS.items()},
        "command_engines": {key: list(value) for key, value in engine.COMMAND_ENGINES.items()},
        "canonical_certification": "NOT_GRANTED",
        "target_runtime_acceptance_required": True,
    }


def main(arguments: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    if not arguments:
        print(__doc__)
        return 2
    if arguments[0] in LEGACY_COMMANDS:
        return run_legacy(arguments)
    if arguments[0] == "engine-status":
        try:
            from engine_runtime_v1 import capability_status_snapshot
            print(json.dumps(engine_status(), ensure_ascii=False, indent=2))
            return 0
        except Exception as exc:
            print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2),
                  file=sys.stderr)
            return 5
    if arguments[0] == "engine-run":
        import argparse
        from engine_gateway_v1 import execute_engine_for_route
        parser = argparse.ArgumentParser(prog="lunita-v1.8 engine-run")
        parser.add_argument("--request", required=True, type=pathlib.Path)
        args = parser.parse_args(arguments[1:])
        try:
            request = json.loads(args.request.read_text(encoding="utf-8"))
            result = execute_engine_for_route(
                request["command"], request["agent"], request["engine_id"], request["payload"]
            )
            audit_record = append_execution_audit(request, result)
            result["audit_event_hash"] = audit_record["event_hash"]
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            print(json.dumps({"status": "DENIED_OR_BLOCKED", "error": str(exc)},
                             ensure_ascii=False, indent=2), file=sys.stderr)
            return 6
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "PASS_ENGINE_OPERATION" else 7
    print(f"Unsupported Lunita v1.8 command: {arguments[0]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
