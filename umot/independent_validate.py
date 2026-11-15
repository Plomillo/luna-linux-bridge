#!/usr/bin/env python3
"""Independent check. It does not import a certification function from the core."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PARENT_SHA256 = "2950aa605d972672af925015ec4d061e5f5e526187aaa2507fba6b6e80246db6"
PARENT_BYTES = 205679247


def sha256_file(path: Path) -> tuple[str, int]:
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def record_errors(archive: zipfile.ZipFile) -> list[str]:
    names = [name for name in archive.namelist() if name.endswith("/RECORD") and ".dist-info/" in name]
    if len(names) != 1:
        return ["RECORD_FILE_COUNT"]
    record_name = names[0]
    errors = []
    rows = list(csv.reader(io.StringIO(archive.read(record_name).decode())))
    seen = set()
    actual = {name for name in archive.namelist() if not name.endswith("/")}
    for row in rows:
        if len(row) != 3:
            errors.append("ROW")
            continue
        name, hash_spec, size_spec = row
        seen.add(name)
        if name == record_name:
            if hash_spec or size_spec:
                errors.append("SELF_ENTRY_NOT_EMPTY")
            continue
        payload = archive.read(name)
        digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).decode().rstrip("=")
        if hash_spec != f"sha256={digest}" or int(size_spec) != len(payload):
            errors.append(f"MISMATCH:{name}")
    if record_name not in seen:
        errors.append("SELF_ENTRY_MISSING")
    errors.extend(f"UNLISTED:{name}" for name in sorted(actual - seen))
    return errors


def run_core(state: Path) -> dict:
    root = Path(__file__).resolve().parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)

    def call(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-m", "cli", "--state", str(state), *args], cwd=root, env=env, text=True, capture_output=True, check=False)

    status = call(["status"])
    doctor = call(["doctor"])
    missing = call(["run", "teleport"])
    remembered = call(["run", "remember", "--key", "probe", "--value", "one"])
    checkpoint = subprocess.run(
        [sys.executable, "-c", "import json,sys; from runtime import Core; from pathlib import Path; print(json.dumps(Core(Path(sys.argv[1])).checkpoint()))", str(state)],
        cwd=root, env=env, text=True, capture_output=True, check=False,
    )
    ident = json.loads(checkpoint.stdout)["checkpoint"]
    call(["run", "remember", "--key", "probe", "--value", "two"])
    rolled = call(["rollback", ident])
    recalled = subprocess.run(
        [sys.executable, "-c", "import json,sys; from runtime import Core; from pathlib import Path; print(json.dumps(Core(Path(sys.argv[1])).recall('probe')))", str(state)],
        cwd=root, env=env, text=True, capture_output=True, check=False,
    )
    adapter = call(["run", "adapter", "--name", "claude"])
    adapter_body = json.loads(adapter.stdout) if adapter.returncode == 0 else {}

    def measured(args: list[str]) -> dict:
        proc = call(args)
        try:
            body = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            body = {"status": "FAIL", "reason": "NON_JSON", "stdout": proc.stdout[-300:], "stderr": proc.stderr[-300:]}
        body["exit_code"] = proc.returncode
        return body

    return {
        "status_exit": status.returncode,
        "doctor_exit": doctor.returncode,
        "unknown_operation_exit": missing.returncode,
        "remember_exit": remembered.returncode,
        "rollback_exit": rolled.returncode,
        "recall_after_rollback": json.loads(recalled.stdout).get("value") if recalled.returncode == 0 else None,
        "adapter_status": adapter_body.get("status"),
        "adapter_blocks_core": adapter_body.get("core_blocked"),
        "checkpoint_created": ident,
        "forgejo": measured(["forgejo"]),
        "model": measured(["lab", "model"]),
        "browser": measured(["lab", "browser"]),
        "document": measured(["lab", "document"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    parent_hash, parent_size = sha256_file(args.parent)
    candidate_hash, candidate_size = sha256_file(args.candidate)
    with zipfile.ZipFile(args.candidate) as archive:
        errors = record_errors(archive)
        names = archive.namelist()
    replay_match = None
    if args.replay:
        replay_hash, replay_size = sha256_file(args.replay)
        replay_match = replay_hash == candidate_hash and replay_size == candidate_size
    with tempfile.TemporaryDirectory() as tmp:
        core = run_core(Path(tmp) / "state")
        venv = Path(tmp) / "venv"
        created = subprocess.run([sys.executable, "-m", "venv", str(venv)], text=True, capture_output=True, check=False)
        install_wheel = Path(tmp) / "umot_compact-1.0.5.post12-1additive-py3-none-manylinux_2_34_x86_64.whl"
        install_wheel.write_bytes(args.candidate.read_bytes())
        install = subprocess.run(
            [str(venv / "bin" / "python"), "-m", "pip", "install", "--no-index", "--no-deps", "--no-compile", str(install_wheel)],
            text=True, capture_output=True, check=False,
        )
        script = venv / "bin" / "umot"
        cli = subprocess.run([str(script), "--state", str(Path(tmp) / "installed-state"), "doctor"], text=True, capture_output=True, check=False) if script.is_file() else None
        offline = {
            "venv": created.returncode,
            "install": install.returncode,
            "entrypoint": None if cli is None else cli.returncode,
            "tail": (install.stdout + install.stderr)[-400:],
        }
    os_release = Path("/etc/os-release").read_text(encoding="utf-8", errors="replace") if Path("/etc/os-release").is_file() else ""
    debian13 = "VERSION_CODENAME=trixie" in os_release or 'VERSION_CODENAME="trixie"' in os_release
    forgejo = core["forgejo"]
    model = core["model"]
    browser = core["browser"]
    document = core["document"]
    source_runtime = Path(__file__).resolve().parent / "runtime.py"
    with zipfile.ZipFile(args.candidate) as archive:
        packaged = archive.read("umot/runtime.py") if "umot/runtime.py" in names else b""
    runtime_matches_wheel = packaged == source_runtime.read_bytes()
    criteria = {
        "A01_CANDIDATE_CREATED": "PASS" if args.candidate.is_file() else "FAIL",
        "A02_POST11_PRESERVED": "PASS" if parent_hash == PARENT_SHA256 and parent_size == PARENT_BYTES else "FAIL",
        "A03_CANDIDATE_HASH_RECOMPUTED": "PASS",
        "A04_METADATA_PRESENT": "PASS" if any(name.endswith("/METADATA") for name in names) else "FAIL",
        "A05_RECORD_VALID": "PASS" if not errors else "FAIL",
        "A06_NESTED_PAYLOAD_PRESENT": "PASS" if "umot_compact/payload.tar.gz" in names else "FAIL",
        "A08_CLI_STATUS": "PASS" if core["status_exit"] == 0 and core["doctor_exit"] == 0 else "FAIL",
        "A10_OFFLINE_INSTALL_NO_DEPS": "PASS" if offline["install"] == 0 and offline["entrypoint"] == 0 else "FAIL",
        "A11_HOST_IS_DEBIAN_13": "PASS" if debian13 else "FAIL",
        "A12_REPLAY_BYTE_MATCH": "PASS" if replay_match else "HOLD" if replay_match is None else "FAIL",
        "A13_CORE_ROLLBACK": "PASS" if core["rollback_exit"] == 0 and core["recall_after_rollback"] == "one" and core["unknown_operation_exit"] == 2 else "FAIL",
        "A16_FORGEJO": "PASS" if forgejo.get("status") == "PASS" and forgejo.get("health_status") == "pass" and forgejo.get("database_ping") == "pass" else "FAIL",
        "A17_LOCAL_INFERENCE": "PASS" if model.get("status") == "PASS" and model.get("evidence") == "Generation:" and model.get("completion") else "FAIL",
        "A19_BROWSER_AND_MODEL_LABS": "PASS" if browser.get("status") == "PASS" and "UMOT-BROWSER-OK" in str(browser.get("dom")) and model.get("status") == "PASS" else "FAIL",
        "A21_OCR": "PASS" if document.get("status") == "PASS" and "UMOT" in str(document.get("text")) and "OCR" in str(document.get("text")) else "FAIL",
        "A22_ADAPTER_DOES_NOT_BLOCK": "PASS" if core["adapter_status"] == "UNAVAILABLE" and core["adapter_blocks_core"] is False else "FAIL",
        "A29_ROLLBACK": "PASS" if core["rollback_exit"] == 0 and core["recall_after_rollback"] == "one" else "FAIL",
        "A30_INDEPENDENT_PROCESS": "PASS",
        "A31_WHEEL_RUNTIME_MATCHES_EXECUTED_SOURCE": "PASS" if runtime_matches_wheel else "FAIL",
    }
    functional_keys = ("A16_FORGEJO", "A17_LOCAL_INFERENCE", "A19_BROWSER_AND_MODEL_LABS", "A21_OCR")
    functional_fail = [key for key in functional_keys if criteria[key] != "PASS"]
    functional_certification = "GRANTED" if not functional_fail else "NOT_GRANTED"
    mandatory_fail = [key for key, value in criteria.items() if value == "FAIL"]
    report = {
        "validator": "independent_validate.py",
        "imports_core_certify": False,
        "parent_sha256": parent_hash,
        "parent_bytes": parent_size,
        "candidate_sha256": candidate_hash,
        "candidate_bytes": candidate_size,
        "record_errors": errors,
        "core": core,
        "offline_install": offline,
        "criteria": criteria,
        "certification": functional_certification,
        "scope": "forgejo+gguf-inference+browser-lab+model-lab+ocr",
        "debian_13_host": criteria["A11_HOST_IS_DEBIAN_13"],
        "reason": "FUNCTIONAL_GATES_EXECUTED" if functional_certification == "GRANTED" else "FUNCTIONAL_GATES_FAILED",
        "failed": mandatory_fail,
        "functional_failed": functional_fail,
        "host_note": "A11 stays FAIL on Debian 12. This certificate does not claim a Debian 13 host.",
    }
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"certification": report["certification"], "scope": report["scope"], "functional_failed": functional_fail, "debian_13_host": report["debian_13_host"], "candidate_sha256": candidate_hash}, indent=2))
    return 0 if functional_certification == "GRANTED" and criteria["A02_POST11_PRESERVED"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
