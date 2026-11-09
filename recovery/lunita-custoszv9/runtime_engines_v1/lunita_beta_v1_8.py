#!/usr/bin/env python3
"""Lunita beta v1.8 additive command wrapper.

Legacy commands are delegated unchanged to the hash-pinned beta v1.7 launcher.
New engine operations are exposed through the command-team-bound E01-E15 gateway.
This file does not replace or rewrite the v1.7 launcher.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Sequence

ROOT = pathlib.Path("/opt/lunita")
OVERLAY = ROOT / "engines/runtime_engines_v1"
LEGACY_LAUNCHER = ROOT / "agent/lunita_beta_v1_7.py"
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
    return env


def run_legacy(arguments: Sequence[str]) -> int:
    if not LEGACY_LAUNCHER.is_file():
        print("DENIED: the preserved beta v1.7 launcher is missing", file=sys.stderr)
        return 2
    observed = sha256_file(LEGACY_LAUNCHER)
    if observed != LEGACY_SHA256:
        print("DENIED: beta v1.7 launcher SHA-256 mismatch", file=sys.stderr)
        return 3
    command = [sys.executable, str(LEGACY_LAUNCHER), *arguments]
    try:
        return subprocess.run(command, env=runtime_environment(), check=False).returncode
    except OSError as exc:
        print(f"DENIED: unable to delegate to beta v1.7: {exc}", file=sys.stderr)
        return 4


def engine_status() -> dict:
    import engine_runtime_v1 as engine
    return {
        "schema": "LUNITA_BETA_V1_8_ENGINE_STATUS/1.0",
        "status": "RUNTIME_CANDIDATE",
        "engine_registry": engine.validate_registry(),
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
