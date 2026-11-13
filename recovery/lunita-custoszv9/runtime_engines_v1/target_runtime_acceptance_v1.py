#!/usr/bin/env python3
"""Required target-side acceptance gate for the G06-derived Lunita beta overlay.

Run after a verified checkpoint and additive overlay receipt exist. A PASS is target-runtime evidence only;
it never issues S32, G23, G24, or canonical G06/G08 certification.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import pathlib
import re
import subprocess
import stat
import sys
import time
import tempfile
import unittest
from datetime import datetime, timezone
from typing import Any

ROOT = pathlib.Path(os.environ.get("LUNITA_ROOT", "/opt/lunita")).expanduser()
OVERLAY = ROOT / "engines/runtime_engines_v1"
STATE = pathlib.Path(os.environ.get("XDG_STATE_HOME") or (pathlib.Path.home() / ".local/state")) / "lunita"
REPORTS = pathlib.Path(os.environ.get("LUNITA_TARGET_RUNTIME_RECEIPT_DIR", str(STATE / "runtime_validation"))).expanduser()
OVERLAY_RECEIPT = OVERLAY / "OVERLAY_APPLY_RECEIPT.json"
LEGACY_LAUNCHER = ROOT / "agent/lunita.py"
EXPECTED_LEGACY_SHA256 = "46efd711729c344e7efba9ce2503127c48f0b88207cc5a17311ff1d555b075b2"
LEGACY_SMOKE_COMMANDS = (
    ("brujula-self-test",),
    ("r-self-test",),
    ("jamovi-self-test",),
    ("jasp-self-test",),
    ("fault", "model-missing"),
    ("fault", "model-corrupted"),
    ("fault", "dependency-missing"),
    ("fault", "permission-denied"),
    ("fault", "low-memory"),
    ("fault", "process-crash"),
    ("fault", "browser-crash"),
    ("fault", "tool-failure"),
    ("fault", "invalid-input"),
    ("fault", "interrupted-execution"),
    ("fault", "restart"),
)
TEST_MODULES = (
    "engine_acceptance_v1",
    "gateway_acceptance_v1",
    "launcher_acceptance_v1",
    "overlay_acceptance_v1",
)

EXPECTED_LABEL_HIERARCHY = {
    "label": "LA PIEZA",
    "children": [{
        "label": "EL ESTUCHE",
        "children": [{
            "label": "UBUNTU 24.04 LTS MINIMAL",
            "children": [{
                "label": "LUNITA LA INVESTIGADORA",
                "children": [
                    {"label": "MOTOR COGNITIVO", "children": [
                        {"label": "Qwen3-0.6B IQ3_XS GGUF",
                         "path": "/opt/lunita/brain/model/Qwen_Qwen3-0.6B-IQ3_XS.gguf"}
                    ]},
                    {"label": "BRÚJULA GIROSCÓPICA", "children": [
                        {"label": "Node.js 22.23.2", "path": "/opt/lunita/instruments/brujula/node/bin/node"},
                        {"label": "Playwright 1.63.0", "path": "/opt/lunita/instruments/brujula/node_modules/playwright"},
                        {"label": "playwright-core 1.63.0", "path": "/opt/lunita/instruments/brujula/node_modules/playwright-core"},
                        {"label": "Chrome for Testing 153.0.8010.12", "path": "/opt/lunita/instruments/brujula/chrome/chrome"}
                    ]},
                    {"label": "LÁPIZ", "children": [
                        {"label": "R 4.6.1", "path": "/opt/lunita/instruments/lapiz/R-4.6.1/bin/Rscript"}
                    ]},
                    {"label": "SACAPUNTAS", "children": [
                        {"label": "jamovi 2.7.27", "application_id": "org.jamovi.jamovi"}
                    ]},
                    {"label": "LUPA", "children": [
                        {"label": "JASP 0.98.8", "application_id": "org.jaspstats.JASP"}
                    ]}
                ]
            }]
        }]
    }]
}

EXPECTED_LABEL_HIERARCHY_TEXT = """LA PIEZA
└── EL ESTUCHE
    └── UBUNTU 24.04 LTS MINIMAL
        └── LUNITA LA INVESTIGADORA
            ├── MOTOR COGNITIVO
            │   └── Qwen3-0.6B IQ3_XS GGUF
            │
            ├── BRÚJULA GIROSCÓPICA
            │   ├── Node.js 22.23.2
            │   ├── Playwright 1.63.0
            │   ├── playwright-core 1.63.0
            │   └── Chrome for Testing 153.0.8010.12
            │
            ├── LÁPIZ
            │   └── R 4.6.1
            │
            ├── SACAPUNTAS
            │   └── jamovi 2.7.27
            │
            └── LUPA
                └── JASP 0.98.8
"""


EXPECTED_JASP_VERSION = "0.98.8"


class TargetGateError(RuntimeError):
    pass


def expected_xdg_runtime_dir() -> str:
    """Derive and cross-check an isolated Flatpak runtime path from GitHub's run identity."""
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if re.fullmatch(r"[0-9]+", run_id) is None or re.fullmatch(r"[0-9]+", run_attempt) is None:
        raise TargetGateError("GITHUB_RUN_ID and GITHUB_RUN_ATTEMPT are missing or unsafe")
    expected_bind_name = f"lunita-host-{run_id}-{run_attempt}"
    host_bind_name = os.environ.get("HOST_BIND_NAME", "")
    if host_bind_name != expected_bind_name:
        raise TargetGateError("HOST_BIND_NAME does not match the explicit GitHub run ID and attempt")
    if re.fullmatch(r"lunita-host-[A-Za-z0-9-]+", host_bind_name) is None:
        raise TargetGateError("HOST_BIND_NAME is unsafe for a runtime mount path")
    return f"/run/{expected_bind_name}-runtime-1000"


def workflow_identity_receipt() -> dict[str, str | None]:
    """Record the exact GitHub workflow attempt that owns this target runtime."""
    return {
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "host_bind_name": os.environ.get("HOST_BIND_NAME"),
        "xdg_runtime_dir": os.environ.get("XDG_RUNTIME_DIR"),
    }


def verify_xdg_runtime_dir() -> dict[str, Any]:
    """Require the Flatpak runtime directory to be a real private UID 1000 directory."""
    expected = expected_xdg_runtime_dir()
    observed = os.environ.get("XDG_RUNTIME_DIR")
    if observed != expected:
        raise TargetGateError(f"XDG_RUNTIME_DIR must be exactly {expected}; observed {observed!r}")
    path = pathlib.Path(observed)
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise TargetGateError(f"XDG_RUNTIME_DIR cannot be inspected: {path}: {exc}") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise TargetGateError("XDG_RUNTIME_DIR must be a real directory, not a symlink or other entry")
    mode = stat.S_IMODE(metadata.st_mode)
    if (metadata.st_uid, metadata.st_gid, mode) != (1000, 1000, 0o700):
        raise TargetGateError(
            "XDG_RUNTIME_DIR must be owned by UID/GID 1000 with mode 0700; "
            f"observed uid={metadata.st_uid} gid={metadata.st_gid} mode={oct(mode)}"
        )
    return {
        "path": str(path),
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "mode_octal": oct(mode),
        "status": "PASS_XDG_RUNTIME_DIR_UID1000_PRIVATE",
    }


def build_target_user_command(
    target_rootfs: pathlib.Path,
    environment: tuple[str, ...] | list[str],
    argv: tuple[str, ...] | list[str],
    *,
    clean_environment: bool = False,
) -> list[str]:
    """Construct a fail-closed UID/GID 1000 command for chroot or pivot-root mode."""
    rootfs = pathlib.Path(target_rootfs)
    pivot_mode = os.environ.get("LUNITA_IN_PIVOT_ROOT") == "1"
    if pivot_mode:
        if os.geteuid() != 0 or rootfs != pathlib.Path("/"):
            raise TargetGateError(
                "Pivot-root execution requires root inside the candidate mount root; refusing a chroot fallback."
            )
        command = [
            "/usr/bin/setpriv", "--reuid=1000", "--regid=1000", "--clear-groups",
            "/usr/bin/env",
        ]
    else:
        command = [
            "sudo", "-n", "chroot", "--userspec=1000:1000", str(rootfs),
            "/usr/bin/env",
        ]
    if clean_environment:
        command.append("-i")
    command.extend(["-C", "/tmp", *environment, *argv])
    return command


def run_target_user_command(
    target_rootfs: pathlib.Path,
    environment: tuple[str, ...] | list[str],
    argv: tuple[str, ...] | list[str],
    *,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run an argv-only command as the actual Lunita UID/GID 1000."""
    return subprocess.run(
        build_target_user_command(target_rootfs, environment, argv),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def write_target_user_json(
    target_rootfs: pathlib.Path,
    request_path: pathlib.Path,
    request: dict[str, Any],
    environment: tuple[str, ...] | list[str],
) -> dict[str, Any]:
    """Create an exclusive, private E01 request as UID 1000 inside its owned XDG directory."""
    target_rootfs = pathlib.Path(target_rootfs)
    request_path = pathlib.Path(request_path)
    expected_parent = target_rootfs / "tmp/lunita-xdg"
    if request_path.parent != expected_parent or not (
        request_path.name.startswith("lunita-e01-qwen-") and request_path.name.endswith(".json")
    ):
        raise TargetGateError("E01 request path must be a unique file directly inside the private target XDG directory")
    writer = (
        "import json, os, pathlib, stat, sys\n"
        "path = pathlib.Path(sys.argv[1])\n"
        "payload = json.loads(sys.argv[2])\n"
        "parent = path.parent.lstat()\n"
        "if not stat.S_ISDIR(parent.st_mode) or (parent.st_uid, parent.st_gid, stat.S_IMODE(parent.st_mode)) != (1000, 1000, 0o700):\n"
        "    raise SystemExit('E01 request parent is not the private UID/GID 1000 XDG directory')\n"
        "flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW\n"
        "fd = os.open(path, flags, 0o600)\n"
        "with os.fdopen(fd, 'w', encoding='utf-8') as stream:\n"
        "    stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + '\\n')\n"
        "    stream.flush()\n"
        "    os.fsync(stream.fileno())\n"
        "created = path.lstat()\n"
        "if not stat.S_ISREG(created.st_mode) or (created.st_uid, created.st_gid, stat.S_IMODE(created.st_mode)) != (1000, 1000, 0o600):\n"
        "    path.unlink(missing_ok=True)\n"
        "    raise SystemExit('E01 request ownership or mode verification failed')\n"
        "print('PASS_TARGET_USER_REQUEST_CREATED')"
    )
    guest_path = pathlib.Path("/tmp/lunita-xdg") / request_path.name
    result = run_target_user_command(
        target_rootfs,
        environment,
        (
            "/usr/bin/python3.12",
            "-c",
            writer,
            str(guest_path),
            json.dumps(request, ensure_ascii=False, sort_keys=True),
        ),
        timeout=30,
    )
    if result.returncode != 0 or "PASS_TARGET_USER_REQUEST_CREATED" not in result.stdout:
        detail = (result.stderr or result.stdout or "no diagnostic output").strip()[-1200:]
        raise TargetGateError("Could not create E01 request as UID 1000: " + detail)
    return {
        "status": "PASS_TARGET_USER_REQUEST_CREATED",
        "path": str(guest_path),
        "owner": "1000:1000",
        "mode": "0600",
    }


def unlink_target_user_request(
    target_rootfs: pathlib.Path,
    request_path: pathlib.Path,
    environment: tuple[str, ...] | list[str],
) -> None:
    """Remove only the exact E01 regular request file as its owning target user."""
    target_rootfs = pathlib.Path(target_rootfs)
    request_path = pathlib.Path(request_path)
    if request_path.parent != target_rootfs / "tmp/lunita-xdg" or not (
        request_path.name.startswith("lunita-e01-qwen-") and request_path.name.endswith(".json")
    ):
        raise TargetGateError("Refusing cleanup outside the private E01 request directory")
    remover = (
        "import pathlib, stat, sys\n"
        "path = pathlib.Path(sys.argv[1])\n"
        "if path.parent != pathlib.Path('/tmp/lunita-xdg'):\n"
        "    raise SystemExit('E01 request cleanup path mismatch')\n"
        "try:\n"
        "    current = path.lstat()\n"
        "except FileNotFoundError:\n"
        "    pass\n"
        "else:\n"
        "    if not stat.S_ISREG(current.st_mode) or (current.st_uid, current.st_gid) != (1000, 1000):\n"
        "        raise SystemExit('E01 request cleanup refused unsafe file')\n"
        "    path.unlink()\n"
        "print('PASS_TARGET_USER_REQUEST_REMOVED')"
    )
    guest_path = pathlib.Path("/tmp/lunita-xdg") / request_path.name
    result = run_target_user_command(
        target_rootfs,
        environment,
        ("/usr/bin/python3.12", "-c", remover, str(guest_path)),
        timeout=15,
    )
    if result.returncode != 0 or "PASS_TARGET_USER_REQUEST_REMOVED" not in result.stdout:
        detail = (result.stderr or result.stdout or "no diagnostic output").strip()[-1000:]
        raise TargetGateError("Could not securely remove E01 request as UID 1000: " + detail)


def build_root_inspection_command(inspector: str, path: pathlib.Path) -> list[str]:
    """Use privileged read-only inspection without leaving the pivot-root candidate."""
    if os.environ.get("LUNITA_IN_PIVOT_ROOT") == "1":
        if os.geteuid() != 0 or ROOT.parents[1] != pathlib.Path("/"):
            raise TargetGateError("Pivot-root inspection is not bound to the actual candidate mount root.")
        prefix = ["/usr/bin/python3"]
    else:
        prefix = ["sudo", "-n", "/usr/bin/python3"]
    return [*prefix, "-c", inspector, str(path)]


def inspect_rootfs_directory_as_root(path: pathlib.Path, label: str) -> dict[str, Any]:
    """Read target-rootfs directory metadata without traversing it as the host runner.

    The target directories are intentionally 0700 and owned by UID/GID 1000.
    The unprivileged GitHub runner cannot stat entries below those directories.
    This performs only a privileged lstat; actual application execution remains
    inside chroot as UID/GID 1000.
    """
    inspector = (
        "import json, os, stat, sys; "
        "s=os.lstat(sys.argv[1]); "
        "print(json.dumps({"
        "'is_symlink': stat.S_ISLNK(s.st_mode), "
        "'is_directory': stat.S_ISDIR(s.st_mode), "
        "'uid': s.st_uid, 'gid': s.st_gid, "
        "'mode': stat.S_IMODE(s.st_mode)"
        "}))"
    )
    try:
        result = subprocess.run(
            build_root_inspection_command(inspector, path),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise TargetGateError(
            f"Cannot inspect {label} with privileged read-only lstat: {path}: {exc}"
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no diagnostic output").strip()[-1000:]
        raise TargetGateError(
            f"Privileged read-only lstat failed for {label}: {path}: {detail}"
        )
    try:
        metadata = json.loads(result.stdout)
    except (TypeError, ValueError) as exc:
        raise TargetGateError(
            f"Privileged lstat returned invalid metadata for {label}: {path}"
        ) from exc
    if not isinstance(metadata, dict):
        raise TargetGateError(f"Privileged lstat returned a non-object for {label}: {path}")
    if metadata.get("is_symlink") is not False or metadata.get("is_directory") is not True:
        raise TargetGateError(f"{label} is missing, not a directory, or symlinked: {path}")
    if (metadata.get("uid") != 1000 or metadata.get("gid") != 1000
            or metadata.get("mode") != 0o700):
        raise TargetGateError(
            f"{label} must be owned by uid/gid 1000 with mode 0700: "
            f"uid={metadata.get('uid')} gid={metadata.get('gid')} "
            f"mode={metadata.get('mode')!r}"
        )
    return metadata


def inspect_rootfs_regular_file_as_root(path: pathlib.Path, label: str) -> dict[str, Any]:
    """Read and hash a private target-rootfs file without traversing it as the host runner.

    The audit log is intentionally 0600 and owned by UID/GID 1000 beneath a 0700
    directory. The host runner cannot read it. This performs a privileged,
    read-only O_NOFOLLOW open, verifies inode stability, and hashes through the
    descriptor; it never changes ownership, permissions, or contents.
    """
    inspector = """
import hashlib
import json
import os
import stat
import sys

path = sys.argv[1]
before = os.lstat(path)
if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
    raise SystemExit("target file is not a regular non-symlink file")
flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
fd = os.open(path, flags)
try:
    opened = os.fstat(fd)
    if not stat.S_ISREG(opened.st_mode):
        raise SystemExit("opened target file is not regular")
    if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
        raise SystemExit("target file changed before read-only inspection")
    digest = hashlib.sha256()
    size = 0
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
        size += len(chunk)
    after = os.fstat(fd)
    stable_before = (opened.st_dev, opened.st_ino, opened.st_size,
                     opened.st_mtime_ns, opened.st_ctime_ns)
    stable_after = (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_ctime_ns)
    if stable_before != stable_after or size != after.st_size:
        raise SystemExit("target file changed while hashing")
    print(json.dumps({
        "is_symlink": False,
        "is_regular_file": stat.S_ISREG(after.st_mode),
        "uid": after.st_uid,
        "gid": after.st_gid,
        "mode": stat.S_IMODE(after.st_mode),
        "size": size,
        "sha256": digest.hexdigest(),
    }))
finally:
    os.close(fd)
"""
    try:
        result = subprocess.run(
            build_root_inspection_command(inspector, path),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise TargetGateError(
            f"Cannot inspect {label} with privileged read-only open: {path}: {exc}"
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no diagnostic output").strip()[-1000:]
        raise TargetGateError(
            f"Privileged read-only file inspection failed for {label}: {path}: {detail}"
        )
    try:
        metadata = json.loads(result.stdout)
    except (TypeError, ValueError) as exc:
        raise TargetGateError(
            f"Privileged file inspection returned invalid metadata for {label}: {path}"
        ) from exc
    if not isinstance(metadata, dict):
        raise TargetGateError(f"Privileged file inspection returned a non-object for {label}: {path}")
    if metadata.get("is_symlink") is not False or metadata.get("is_regular_file") is not True:
        raise TargetGateError(f"{label} is missing, not a regular file, or symlinked: {path}")
    if (metadata.get("uid") != 1000 or metadata.get("gid") != 1000
            or metadata.get("mode") != 0o600):
        raise TargetGateError(
            f"{label} must be owned by uid/gid 1000 with mode 0600: "
            f"uid={metadata.get('uid')} gid={metadata.get('gid')} "
            f"mode={metadata.get('mode')!r}"
        )
    if not isinstance(metadata.get("size"), int) or metadata["size"] <= 0:
        raise TargetGateError(f"{label} must contain a non-empty audit record: {path}")
    digest = metadata.get("sha256")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)):
        raise TargetGateError(f"{label} returned an invalid SHA-256 digest: {path}")
    return metadata


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_directory(path: pathlib.Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_dir():
        raise TargetGateError(f"Required overlay directory is missing or symlinked: {path}")
    entries = []
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise TargetGateError(f"Symlink found in installed engine overlay: {item}")
        if item.is_file():
            entries.append({
                "path": item.relative_to(path).as_posix(),
                "sha256": sha256_file(item),
                "bytes": item.stat().st_size,
            })
        elif not item.is_dir():
            raise TargetGateError(f"Unexpected filesystem entry in overlay: {item}")
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "file_count": len(entries),
        "bytes": sum(entry["bytes"] for entry in entries),
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }


def verify_system_python_alias(rootfs: pathlib.Path) -> dict[str, str]:
    """Require Ubuntu's system python3 entrypoint to resolve to the pinned 3.12 runtime."""
    python3 = rootfs / "usr/bin/python3"
    python312 = rootfs / "usr/bin/python3.12"
    if not python3.is_symlink():
        raise TargetGateError("Ubuntu system /usr/bin/python3 compatibility symlink is missing")
    if not python312.is_file() or not os.access(python312, os.X_OK):
        raise TargetGateError("Ubuntu target /usr/bin/python3.12 is missing or not executable")
    try:
        observed = python3.resolve(strict=True)
        expected = python312.resolve(strict=True)
    except OSError as exc:
        raise TargetGateError(f"Ubuntu system python3 symlink is broken: {exc}") from exc
    if observed != expected:
        raise TargetGateError(
            "Ubuntu system /usr/bin/python3 must resolve to /usr/bin/python3.12; "
            f"observed={observed} expected={expected}"
        )
    return {
        "status": "PASS_SYSTEM_PYTHON_ALIAS",
        "default_executable": "/usr/bin/python3",
        "symlink_target": os.readlink(python3),
        "resolved_executable": str(observed),
    }


def validate_label_hierarchy_document(document: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless the exact requested identity hierarchy is preserved."""
    if not isinstance(document, dict):
        raise TargetGateError("LUNITA label hierarchy is not a JSON object")
    if document.get("schema") != "LUNITA_LABEL_HIERARCHY/1.0":
        raise TargetGateError("LUNITA label hierarchy schema mismatch")
    if document.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1" or document.get("version") != "1.8.0":
        raise TargetGateError("LUNITA label hierarchy candidate identity mismatch")
    if document.get("preservation_policy") != "APPEND_ONLY;DO_NOT_REWRITE_EXISTING_LABELS":
        raise TargetGateError("LUNITA label hierarchy preservation policy mismatch")
    if document.get("hierarchy") != EXPECTED_LABEL_HIERARCHY:
        raise TargetGateError("LUNITA label hierarchy differs from the exact requested labels or mappings")
    if document.get("rendered_tree") != EXPECTED_LABEL_HIERARCHY_TEXT:
        raise TargetGateError("LUNITA rendered label tree differs from the exact requested hierarchy")
    labels: list[str] = []
    def walk(node: dict[str, Any]) -> None:
        if not isinstance(node, dict) or not isinstance(node.get("label"), str):
            raise TargetGateError("LUNITA label hierarchy contains a malformed node")
        labels.append(node["label"])
        children = node.get("children", [])
        if not isinstance(children, list):
            raise TargetGateError("LUNITA label hierarchy children must be an array")
        for child in children:
            walk(child)
    walk(document["hierarchy"])
    return {"status": "PASS_EXACT_LABEL_HIERARCHY", "labels": labels, "label_count": len(labels)}


def verify_label_hierarchy(receipt: dict[str, Any]) -> dict[str, Any]:
    binding = receipt.get("label_hierarchy", {})
    json_path = ROOT / "metadata/LUNITA_LABEL_HIERARCHY.json"
    text_path = ROOT / "metadata/LUNITA_LABEL_HIERARCHY.txt"
    if binding.get("schema") != "LUNITA_LABEL_HIERARCHY/1.0":
        raise TargetGateError("Rootfs receipt does not bind the requested LUNITA label hierarchy")
    if binding.get("json_path") != "/opt/lunita/metadata/LUNITA_LABEL_HIERARCHY.json":
        raise TargetGateError("Rootfs label hierarchy JSON path mismatch")
    if binding.get("text_path") != "/opt/lunita/metadata/LUNITA_LABEL_HIERARCHY.txt":
        raise TargetGateError("Rootfs label hierarchy text path mismatch")
    for path, expected_sha, label in (
        (json_path, binding.get("json_sha256"), "JSON"),
        (text_path, binding.get("text_sha256"), "text"),
    ):
        if path.is_symlink() or not path.is_file():
            raise TargetGateError(f"Exact LUNITA label hierarchy {label} file is missing or unsafe")
        if not isinstance(expected_sha, str) or sha256_file(path) != expected_sha:
            raise TargetGateError(f"Exact LUNITA label hierarchy {label} digest mismatch")
    try:
        document = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TargetGateError(f"Exact LUNITA label hierarchy JSON is unreadable: {exc}") from exc
    result = validate_label_hierarchy_document(document)
    if text_path.read_text(encoding="utf-8") != EXPECTED_LABEL_HIERARCHY_TEXT:
        raise TargetGateError("Exact LUNITA label hierarchy text file is not preserved")
    return {
        **result,
        "json_sha256": binding["json_sha256"],
        "text_sha256": binding["text_sha256"],
        "existing_instrument_labels_preserved": True,
        "certification": "NOT_GRANTED",
    }


def verify_rootfs_build_receipt() -> dict[str, Any]:
    """Verify the reconstructed rootfs provenance and every declared major runtime payload."""
    path = ROOT / "metadata/ROOTFS_BUILD_RECEIPT.json"
    if path.is_symlink() or not path.is_file():
        raise TargetGateError("Rootfs build receipt is missing or not a regular file")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "LUNITA_ROOTFS_BUILD_RECEIPT/1.0":
        raise TargetGateError("Rootfs build receipt schema mismatch")
    if receipt.get("status") != "PASS_ROOTFS_BUILD_NOT_CERTIFIED":
        raise TargetGateError("Rootfs builder did not report an accepted build")
    if receipt.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1":
        raise TargetGateError("Rootfs build candidate identity mismatch")
    if receipt.get("source_rootfs_recovered") is not False:
        raise TargetGateError("Rebuilt rootfs provenance is ambiguous")
    ubuntu = receipt.get("ubuntu", {})
    if ubuntu.get("release") != "24.04" or ubuntu.get("codename") != "noble" or ubuntu.get("architecture") != "amd64":
        raise TargetGateError("Rootfs is not the registered Ubuntu 24.04 amd64 baseline")
    target_rootfs = ROOT.parents[1]
    tmp_path = target_rootfs / "tmp"
    if tmp_path.is_symlink() or not tmp_path.is_dir():
        raise TargetGateError("Ubuntu target-rootfs /tmp is missing, unsafe, or not a directory")
    tmp_stat = tmp_path.lstat()
    tmp_mode = stat.S_IMODE(tmp_stat.st_mode)
    tmp_receipt = receipt.get("filesystem_permissions", {}).get("tmp_directory", {})
    if ((tmp_stat.st_uid, tmp_stat.st_gid, tmp_mode) != (0, 0, 0o1777)
            or tmp_receipt != {"path": "/tmp", "uid": 0, "gid": 0, "mode_octal": "01777"}):
        raise TargetGateError(
            "Ubuntu target-rootfs /tmp permissions are not the required root-owned 01777 sticky directory"
        )
    system_python = verify_system_python_alias(target_rootfs)
    python_receipt = receipt.get("system_python", {})
    if (python_receipt.get("default_executable") != "/usr/bin/python3"
            or python_receipt.get("symlink_target") != "python3.12"
            or not str(python_receipt.get("version_output", "")).startswith("Python 3.12.")):
        raise TargetGateError("Rootfs build receipt does not bind the Ubuntu Python 3.12 system alias")

    def require_hash(relative: str, expected: str, label: str) -> pathlib.Path:
        target = pathlib.Path(relative)
        if target.is_absolute():
            full = target
        else:
            full = ROOT / target
        if full.is_symlink() or not full.is_file():
            raise TargetGateError(f"Required rootfs payload is missing: {label}")
        observed = sha256_file(full)
        if not isinstance(expected, str) or observed != expected:
            raise TargetGateError(f"Rootfs payload digest mismatch: {label}")
        return full

    launcher = receipt.get("legacy_launcher", {})
    require_hash("agent/lunita.py", launcher.get("sha256"), "legacy beta-v1.7 launcher")
    qwen = receipt.get("qwen", {})
    if qwen.get("quantization") != "IQ3_XS" or qwen.get("revision") != "f9184d8b4c371cb52af5b8cb3d38e55e3cf0f4a0":
        raise TargetGateError("Qwen model source identity or quantization is not pinned")
    model = require_hash("brain/model/Qwen_Qwen3-0.6B-IQ3_XS.gguf", qwen.get("sha256"), "Qwen3 IQ3_XS model")
    if model.stat().st_size != qwen.get("bytes"):
        raise TargetGateError("Qwen model byte count differs from the build receipt")

    llama = receipt.get("llama_cpp", {})
    if llama.get("commit") != "cd959bae99ff4bed22bef2604f45241c09bbb8c8":
        raise TargetGateError("llama.cpp source commit is not pinned to the registered release")
    llama_candidates = list((ROOT / "brain/runtime").rglob("llama-cli"))
    if len(llama_candidates) != 1:
        raise TargetGateError(f"Expected exactly one packaged llama-cli, found {len(llama_candidates)}")
    require_hash(str(llama_candidates[0]), llama.get("llama_cli_sha256"), "llama.cpp llama-cli")

    brujula = receipt.get("brujula", {})
    if brujula.get("node") != "v22.23.2" or brujula.get("playwright") != "1.63.0" or brujula.get("playwright_core") != "1.63.0":
        raise TargetGateError("Brújula Node/Playwright versions do not match the registered runtime")
    browser_root = ROOT / "instruments/brujula"
    require_hash("instruments/brujula/node/bin/node", brujula.get("node_binary_sha256"), "Node.js binary")
    require_hash("instruments/brujula/chrome/chrome", brujula.get("chrome_binary_sha256"), "Chrome for Testing binary")
    for package in ("playwright", "playwright-core"):
        metadata = browser_root / "node_modules" / package / "package.json"
        if metadata.is_symlink() or not metadata.is_file():
            raise TargetGateError(f"Brújula package is missing: {package}")
        if json.loads(metadata.read_text(encoding="utf-8")).get("version") != "1.63.0":
            raise TargetGateError(f"Brújula package version mismatch: {package}")
    target_rootfs = ROOT.parents[1]

    def run_as_lunita(*argv: str, extra_env: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
        environment = (
            "HOME=/home/lunita",
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "XDG_CACHE_HOME=/tmp/lunita-xdg/cache",
            "XDG_CONFIG_HOME=/tmp/lunita-xdg/config",
            "XDG_DATA_HOME=/tmp/lunita-xdg/data",
            f"XDG_RUNTIME_DIR={expected_xdg_runtime_dir()}",
            "FLATPAK_SYSTEM_DIR=/var/lib/flatpak",
            *extra_env,
        )
        return subprocess.run(
            build_target_user_command(target_rootfs, environment, argv),
            capture_output=True, text=True, check=False,
        )

    guest_node = "/opt/lunita/instruments/brujula/node/bin/node"
    guest_chrome = "/opt/lunita/instruments/brujula/chrome/chrome"
    node_result = run_as_lunita(guest_node, "--version")
    if node_result.returncode != 0 or node_result.stdout.strip() != "v22.23.2":
        raise TargetGateError("Node.js target-rootfs runtime did not return the pinned version")
    chrome_result = run_as_lunita(guest_chrome, "--version")
    if chrome_result.returncode != 0 or "153.0.8010.12" not in chrome_result.stdout:
        raise TargetGateError("Chrome for Testing target-rootfs executable did not return the pinned version")

    lapiz = receipt.get("lapiz", {})
    if lapiz.get("r_version") != "4.6.1":
        raise TargetGateError("Lápiz R version is not pinned to 4.6.1")
    rscript = require_hash("instruments/lapiz/R-4.6.1/bin/Rscript", lapiz.get("rscript_sha256"), "Rscript binary")
    r_home = "/opt/lunita/instruments/lapiz/R-4.6.1/lib/R"
    r = run_as_lunita(
        "/opt/lunita/instruments/lapiz/R-4.6.1/bin/Rscript",
        "-e", 'stopifnot(as.character(getRversion())=="4.6.1", 2+2==4)',
        extra_env=(f"R_HOME={r_home}",),
    )
    if r.returncode != 0:
        raise TargetGateError("Lápiz R 4.6.1 execution failed: " + (r.stderr or r.stdout)[-1200:])

    apps = (
        ("org.jamovi.jamovi", "sacapuntas", "2.7.27"),
        ("org.jaspstats.JASP", "lupa", EXPECTED_JASP_VERSION),
    )
    observed_apps = {}
    for app_id, key, expected_version in apps:
        value = receipt.get(key, {})
        if value.get("application_id") != app_id or value.get("version") != expected_version:
            raise TargetGateError(f"Flatpak app identity/version mismatch: {app_id}")
        if not (pathlib.Path(os.environ.get("FLATPAK_SYSTEM_DIR", "/var/lib/flatpak")) / "app" / app_id).is_dir():
            raise TargetGateError(f"Flatpak system deployment is missing: {app_id}")
        if value.get("version_source") != "EXACT_PINNED_FLATPAK_COMMIT_MAPPING":
            raise TargetGateError(f"Flatpak version is not bound to its recorded commit mapping: {app_id}")
        info = subprocess.run(
            ["/usr/bin/flatpak", "info", "--system", "--show-commit", app_id],
            capture_output=True, text=True, check=False,
        )
        if info.returncode != 0:
            raise TargetGateError(f"Flatpak could not inspect the target system app: {app_id}")
        if info.stdout.strip() != value.get("flatpak_commit"):
            raise TargetGateError(f"Flatpak installed commit mismatch: {app_id}")
        observed_apps[app_id] = {
            "version": expected_version,
            "version_source": value.get("version_source"),
            "commit": info.stdout.strip(),
        }

    label_hierarchy = verify_label_hierarchy(receipt)
    invariants = receipt.get("invariants", {})
    if any(invariants.get(flag) is not False for flag in (
        "frozen_g06_mutated", "canonical_g08_mutated", "legacy_launcher_replaced",
        "canonical_certification_inherited",
    )):
        raise TargetGateError("Rootfs build receipt does not preserve frozen/canonical identity")

    return {
        "status": "PASS_ROOTFS_BUILD_IDENTITY",
        "receipt_sha256": sha256_file(path),
        "source_rootfs_recovered": False,
        "system_python": system_python,
        "ubuntu": ubuntu,
        "qwen_model_sha256": sha256_file(model),
        "llama_cli_sha256": sha256_file(llama_candidates[0]),
        "node_version": brujula.get("node"),
        "playwright_version": brujula.get("playwright"),
        "chrome_version": brujula.get("chrome_for_testing"),
        "r_version": lapiz.get("r_version"),
        "flatpak_apps": observed_apps,
        "label_hierarchy": label_hierarchy,
        "certification": "NOT_GRANTED",
    }


def verify_e04_quantization_receipt() -> dict[str, Any]:
    cache = OVERLAY / "model-cache/fastembed"
    receipt_path = cache / "LUNITA_E04_ONNX_QUANTIZATION_RECEIPT.json"
    relative_model = pathlib.Path(
        "models--Qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q/"
        "snapshots/faf4aa4225822f3bc6376869cb1164e8e3feedd0/model_optimized.onnx"
    )
    model_path = cache / relative_model
    if receipt_path.is_symlink() or model_path.is_symlink() or not receipt_path.is_file() or not model_path.is_file():
        raise TargetGateError("Measured INT8 E04 model or regular quantization receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS_INT8_QUANTIZATION_MEASURED":
        raise TargetGateError("E04 quantization receipt is not a measured PASS")
    if receipt.get("model_id") != "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2":
        raise TargetGateError("E04 model identity mismatch")
    if receipt.get("model_cache_relative_path") != relative_model.as_posix():
        raise TargetGateError("E04 model snapshot path is not the registered pinned snapshot")
    if receipt.get("embedding_dimension") != 384:
        raise TargetGateError("E04 embedding dimension mismatch")
    if receipt.get("quantization") != "ONNX_RUNTIME_DYNAMIC_QINT8_PER_CHANNEL":
        raise TargetGateError("Unexpected E04 quantization method")
    if sha256_file(model_path) != receipt.get("quantized_sha256"):
        raise TargetGateError("E04 ONNX quantized model digest mismatch")
    validation = receipt.get("onnx_validation", {})
    if validation.get("onnxruntime_load_status") != "PASS":
        raise TargetGateError("ONNX Runtime did not load the quantized model")
    if not isinstance(validation.get("int8_initializer_count"), int) or validation["int8_initializer_count"] < 1:
        raise TargetGateError("INT8 model contains no measured quantized weight initializers")
    if not validation.get("quantized_operator_counts"):
        raise TargetGateError("INT8 model contains no quantized ONNX operators")
    if validation.get("checker_status") not in {
        "PASS_ONNX_CHECKER",
        "KNOWN_ONNX_SCHEMA_REGISTRY_GAP_LAYER_NORMALIZATION_OPSET11",
    }:
        raise TargetGateError("Unsupported ONNX graph validation status")
    thresholds = receipt.get("thresholds", {})
    mean_min = thresholds.get("minimum_mean_vector_cosine")
    vector_min = thresholds.get("minimum_vector_cosine")
    retrieval_required = thresholds.get("required_retrieval_top1_agreement")
    size_max = thresholds.get("maximum_model_size_ratio")
    if not isinstance(mean_min, (int, float)) or receipt.get("mean_vector_cosine", 0) < mean_min:
        raise TargetGateError("E04 mean vector cosine fell below the measured threshold")
    if not isinstance(vector_min, (int, float)) or receipt.get("minimum_vector_cosine", 0) < vector_min:
        raise TargetGateError("E04 minimum vector cosine fell below the measured threshold")
    if receipt.get("retrieval_top1_agreement") != retrieval_required:
        raise TargetGateError("E04 retrieval top-1 agreement did not meet the registered threshold")
    if not isinstance(size_max, (int, float)) or receipt.get("size_ratio", 1) >= size_max:
        raise TargetGateError("E04 INT8 model did not meet the registered size-reduction threshold")
    if receipt.get("quantized_bytes") != model_path.stat().st_size or receipt.get("original_bytes", 0) <= 0:
        raise TargetGateError("E04 quantized model size is not bound to the receipt")
    observed_ratio = receipt["quantized_bytes"] / receipt["original_bytes"]
    if abs(observed_ratio - receipt.get("size_ratio", -1)) > 1e-9:
        raise TargetGateError("E04 quantized model size ratio does not match its byte counts")
    decisions = receipt.get("retrieval_decisions", [])
    if len(decisions) != receipt.get("query_count") or len(decisions) != 10:
        raise TargetGateError("E04 retrieval evidence is incomplete")
    if not all(item.get("top1_match") for item in decisions):
        raise TargetGateError("E04 retrieval corpus contains a top-1 regression")
    return {
        "status": "PASS_E04_INT8_QUALITY_GATE",
        "receipt_sha256": sha256_file(receipt_path),
        "model_sha256": sha256_file(model_path),
        "onnx_validation": validation,
        "mean_vector_cosine": receipt["mean_vector_cosine"],
        "minimum_vector_cosine": receipt["minimum_vector_cosine"],
        "retrieval_top1_agreement": receipt["retrieval_top1_agreement"],
        "size_ratio": receipt["size_ratio"],
    }


def verify_overlay() -> dict[str, Any]:
    if not OVERLAY_RECEIPT.is_file():
        raise TargetGateError("Additive overlay receipt is missing")
    receipt = json.loads(OVERLAY_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("schema") != "LUNITA_ADDITIVE_ENGINE_OVERLAY_RECEIPT/1.0":
        raise TargetGateError("Overlay receipt schema mismatch")
    if receipt.get("status") != "APPLIED_ADDITIVELY_NOT_CERTIFIED":
        raise TargetGateError("Overlay receipt status is not APPLIED_ADDITIVELY_NOT_CERTIFIED")
    if receipt.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1":
        raise TargetGateError("Overlay candidate identity mismatch")
    if receipt.get("certification") != "NOT_GRANTED":
        raise TargetGateError("Unexpected inherited certification in additive overlay")
    if receipt.get("launcher_sha256") != EXPECTED_LEGACY_SHA256:
        raise TargetGateError("Legacy launcher digest in overlay receipt mismatch")
    observed_launcher = sha256_file(LEGACY_LAUNCHER)
    if observed_launcher != EXPECTED_LEGACY_SHA256:
        raise TargetGateError("Installed legacy launcher SHA-256 mismatch")
    required_files = {
        "__init__.py", "engine_runtime_v1.py", "engine_acceptance_v1.py",
        "engine_gateway_v1.py", "gateway_acceptance_v1.py", "lunita_beta_v1_8.py",
        "launcher_acceptance_v1.py", "target_runtime_acceptance_v1.py",
        "apply_engine_overlay_v1.py", "checkpoint_v1.py", "overlay_acceptance_v1.py",
        "engine_assignments_v1.json", "requirements-engine-stack.txt",
        "DEPENDENCY_EVIDENCE_v1.json", "ENGINE_RUNTIME_V1_README.md",
    }
    files = receipt.get("files")
    if not isinstance(files, dict) or set(files) != required_files:
        raise TargetGateError("Overlay file manifest is incomplete or contains unexpected entries")
    for relative, expected in files.items():
        path = OVERLAY / relative
        if path.is_symlink() or not path.is_file() or sha256_file(path) != expected:
            raise TargetGateError(f"Installed overlay file hash mismatch: {relative}")
    required_directories = {"vendor/python3.12/site-packages", "model-cache/fastembed"}
    directories = receipt.get("directories")
    if not isinstance(directories, dict) or set(directories) != required_directories:
        raise TargetGateError("Overlay directory manifest is incomplete or unexpected")
    for relative, expected in directories.items():
        actual = hash_directory(OVERLAY / relative)
        if actual != expected:
            raise TargetGateError(f"Installed overlay directory hash mismatch: {relative}")
    immutable_flags = (
        "canonical_identity_mutation", "engine_reassignment", "command_reassignment",
        "agent_reassignment", "frozen_g06_mutated", "canonical_g08_mutated",
        "launcher_mutated", "model_weights_mutated",
    )
    if any(receipt.get(flag) is not False for flag in immutable_flags):
        raise TargetGateError("Overlay receipt does not prove all frozen identity and artifact invariants")
    return {
        "status": "PASS_OVERLAY_INTEGRITY",
        "receipt_sha256": sha256_file(OVERLAY_RECEIPT),
        "legacy_launcher_sha256": observed_launcher,
        "directory_integrity": "PASS",
        "frozen_g06_mutated": receipt.get("frozen_g06_mutated"),
        "canonical_g08_mutated": receipt.get("canonical_g08_mutated"),
    }


REQUIRED_ENGINE_TEST_MATCHERS = {
    "E02": "test_e02_spanish_nlp_executes_tokenization_morphology_and_pos",
    "E03": "test_e03_rag_returns_source_bound_context",
    "E04": "test_e04_embedding_and_e05_vector_search_execute_real_models",
    "E05": "test_e04_embedding_and_e05_vector_search_execute_real_models",
    "E06": "test_e06_knowledge_graph_executes_paths",
    "E07": "test_e07_rdf_parse_serialize_and_sparql",
    "E08": "test_e08_owl_profile_validates_explicit_classes_and_properties",
    "E09": "test_e09_owlrl_semantic_inference_materializes_subclass_entailment",
    "E10": "test_e10_safe_rule_engine_converges_without_eval",
    "E11": "test_e11_hermeneutic_separates_source_context_and_hypothesis",
    "E12": "test_e12_formalization_builds_symbolic_expression_without_eval",
    "E13": "test_e13_json_schema_validation_positive_and_negative",
    "E14": "test_e14_provenance_chain_detects_tampering",
    "E15": "test_e15_consensus_requires_all_assigned_votes_and_same_evidence",
}


def _flatten_test_ids(suite) -> list[str]:
    identifiers = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            identifiers.extend(_flatten_test_ids(item))
        else:
            identifiers.append(item.id())
    return identifiers


def run_unittests() -> dict[str, Any]:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for module_name in TEST_MODULES:
        module = importlib.import_module(module_name)
        suite.addTests(loader.loadTestsFromModule(module))
    test_ids = _flatten_test_ids(suite)
    engine_ids_covered = sorted(
        engine_id for engine_id, matcher in REQUIRED_ENGINE_TEST_MATCHERS.items()
        if any(matcher in test_id for test_id in test_ids)
    )
    command_route_matrix_test = any(
        "test_complete_canonical_route_matrix_for_all_fourteen_commands" in test_id
        for test_id in test_ids
    )
    missing_engine_ids = sorted(set(REQUIRED_ENGINE_TEST_MATCHERS) - set(engine_ids_covered))
    # Never run acceptance tests against the user's persistent vector database.
    # Each target-validation run receives a fresh, disposable Qdrant directory.
    previous_vector_path = os.environ.get("LUNITA_VECTOR_DB_PATH")
    with tempfile.TemporaryDirectory(prefix="lunita-target-engine-tests-") as vector_db:
        os.environ["LUNITA_VECTOR_DB_PATH"] = vector_db
        try:
            result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
        finally:
            if previous_vector_path is None:
                os.environ.pop("LUNITA_VECTOR_DB_PATH", None)
            else:
                os.environ["LUNITA_VECTOR_DB_PATH"] = previous_vector_path
    return {
        "status": (
            "PASS"
            if result.wasSuccessful() and not result.skipped
            and not missing_engine_ids and command_route_matrix_test
            else "FAIL"
        ),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "engine_ids_covered": engine_ids_covered,
        "required_engine_ids": sorted(REQUIRED_ENGINE_TEST_MATCHERS),
        "missing_engine_ids": missing_engine_ids,
        "command_route_matrix_test_present": command_route_matrix_test,
        "failure_test_ids": [test.id() for test, _ in result.failures],
        "error_test_ids": [test.id() for test, _ in result.errors],
        "skipped_test_ids": [test.id() for test, _ in result.skipped],
        "test_ids": test_ids,
    }


def run_qwen_via_v18() -> dict[str, Any]:
    """Execute E01 through the installed v1.8 gateway inside the target rootfs."""
    model = ROOT / "brain/model/Qwen_Qwen3-0.6B-IQ3_XS.gguf"
    if not model.is_file():
        raise TargetGateError(f"Required Qwen model is missing: {model}")
    target_rootfs = ROOT.parents[1]
    xdg_root = target_rootfs / "tmp/lunita-xdg"
    audit_dir = xdg_root / "audit"
    for directory, label in ((xdg_root, "XDG runtime root"), (audit_dir, "append-only audit directory")):
        inspect_rootfs_directory_as_root(directory, label)
    request = {
        "command": "/play PT",
        "agent": "Luna",
        "engine_id": "E01",
        "payload": {
            "prompt": "Responde únicamente OK.",
            "max_tokens": 4,
            "timeout_seconds": 120,
        },
    }
    request_path = xdg_root / f"lunita-e01-qwen-{time.time_ns()}.json"
    target_environment = (
        "HOME=/home/lunita",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "XDG_CACHE_HOME=/tmp/lunita-xdg/cache",
        "XDG_CONFIG_HOME=/tmp/lunita-xdg/config",
        "XDG_DATA_HOME=/tmp/lunita-xdg/data",
        f"XDG_RUNTIME_DIR={expected_xdg_runtime_dir()}",
        "XDG_STATE_HOME=/tmp/lunita-xdg/state",
        "TMPDIR=/tmp/lunita-xdg",
        "LUNITA_ROOT=/opt/lunita",
        "LUNITA_FASTEMBED_CACHE=/opt/lunita/engines/runtime_engines_v1/model-cache/fastembed",
        "LUNITA_VECTOR_DB_PATH=/tmp/lunita-xdg/vectors",
        "LUNITA_ENGINE_AUDIT_LOG=/tmp/lunita-xdg/audit/engine-execution.jsonl",
        "PYTHONPATH=/opt/lunita/engines/runtime_engines_v1/vendor/python3.12/site-packages:/opt/lunita/engines/runtime_engines_v1",
        "HF_HUB_OFFLINE=1",
        "TRANSFORMERS_OFFLINE=1",
        "HF_HUB_DISABLE_TELEMETRY=1",
    )
    write_target_user_json(target_rootfs, request_path, request, target_environment)
    try:
        proc = run_target_user_command(
            target_rootfs,
            target_environment,
            (
                "/usr/bin/python3.12",
                "/opt/lunita/engines/runtime_engines_v1/lunita_beta_v1_8.py",
                "engine-run", "--request", "/" + request_path.relative_to(target_rootfs).as_posix(),
            ),
            timeout=180,
        )
    finally:
        unlink_target_user_request(target_rootfs, request_path, target_environment)

    if proc.returncode != 0:
        raise TargetGateError("E01 Qwen inference failed inside target rootfs: " + (proc.stderr or proc.stdout)[-2000:])
    try:
        result = json.loads(proc.stdout)
    except ValueError as exc:
        raise TargetGateError("E01 target-rootfs gateway did not return valid JSON") from exc
    if result.get("status") != "PASS_ENGINE_OPERATION" or result.get("engine_id") != "E01":
        raise TargetGateError("E01 gateway did not return PASS_ENGINE_OPERATION")
    if not result.get("audit_event_hash"):
        raise TargetGateError("E01 execution did not produce a provenance audit hash")
    payload = result.get("result", {})
    output = payload.get("output", "")
    if payload.get("returncode") != 0 or not output.strip():
        raise TargetGateError("Qwen returned no generated output")
    audit = target_rootfs / "tmp/lunita-xdg/audit/engine-execution.jsonl"
    audit_metadata = inspect_rootfs_regular_file_as_root(
        audit, "append-only target-rootfs engine audit log"
    )
    llama_candidates = list((ROOT / "brain/runtime").rglob("llama-cli"))
    if len(llama_candidates) != 1:
        raise TargetGateError(f"Expected exactly one target-rootfs llama-cli, found {len(llama_candidates)}")
    return {
        "status": "PASS_E01_QWEN_INFERENCE",
        "execution_environment": (
            "PIVOT_ROOT_UBUNTU_24_04_UID_1000"
            if os.environ.get("LUNITA_IN_PIVOT_ROOT") == "1"
            else "CHROOT_UBUNTU_24_04_UID_1000"
        ),
        "model": model.name,
        "model_sha256": sha256_file(model),
        "llama_cli_sha256": sha256_file(llama_candidates[0]),
        "prompt_sha256": payload["prompt_sha256"],
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "audit_event_hash": result["audit_event_hash"],
        "audit_log_sha256": audit_metadata["sha256"],
    }


def diagnose_flatpak_smoke(app_id: str) -> dict[str, Any]:
    """Capture the sandbox failure with inherited and clean guest environments."""
    if app_id not in {"org.jamovi.jamovi", "org.jaspstats.JASP"}:
        raise TargetGateError(f"Unsupported Flatpak diagnostic application: {app_id}")
    target_rootfs = ROOT.parents[1]
    guest_environment = (
        "HOME=/home/lunita",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "XDG_CACHE_HOME=/tmp/lunita-xdg/cache",
        "XDG_CONFIG_HOME=/tmp/lunita-xdg/config",
        "XDG_DATA_HOME=/tmp/lunita-xdg/data",
        f"XDG_RUNTIME_DIR={expected_xdg_runtime_dir()}",
        "XDG_STATE_HOME=/tmp/lunita-xdg/state",
        "FLATPAK_SYSTEM_DIR=/var/lib/flatpak",
        "TMPDIR=/tmp",
        "LANG=C.UTF-8",
        "LC_ALL=C.UTF-8",
    )
    results = {}
    for clean_environment in (False, True):
        command = build_target_user_command(
            target_rootfs,
            guest_environment,
            (
                "/usr/bin/flatpak", "--system", "run", "--command=sh",
                app_id, "-c", "test -d /app",
            ),
            clean_environment=clean_environment,
        )
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=90, check=False
            )
            results["clean" if clean_environment else "inherited"] = {
                "returncode": result.returncode,
                "stdout": (result.stdout or "")[-1200:],
                "stderr": (result.stderr or "")[-1600:],
            }
        except (OSError, subprocess.SubprocessError) as exc:
            results["clean" if clean_environment else "inherited"] = {
                "returncode": None, "error_type": type(exc).__name__,
                "error": str(exc)[:1200],
            }
    return {
        "application_id": app_id,
        "execution_user": "1000:1000",
        "diagnostic_only": True,
        "does_not_change_flatpak_commit_or_permissions": True,
        "runs": results,
    }


def run_legacy_smokes() -> dict[str, Any]:
    import lunita_beta_v1_8 as launcher
    if launcher.sha256_file(LEGACY_LAUNCHER) != EXPECTED_LEGACY_SHA256:
        raise TargetGateError("Legacy launcher hash check failed before application smoke tests")
    results = {}
    for arguments in LEGACY_SMOKE_COMMANDS:
        command = " ".join(arguments)
        rc = launcher.run_legacy(list(arguments))
        results[command] = {"returncode": rc, "status": "PASS" if rc == 0 else "FAIL"}
        if rc != 0:
            details = {}
            if command in {"jamovi-self-test", "jasp-self-test"}:
                details = diagnose_flatpak_smoke({
                    "jamovi-self-test": "org.jamovi.jamovi",
                    "jasp-self-test": "org.jaspstats.JASP",
                }[command])
            diagnostic_text = json.dumps(details, ensure_ascii=False, sort_keys=True)
            raise TargetGateError(
                f"Legacy application/fault smoke test failed: {command} rc={rc}; "
                f"flatpak_diagnostic={diagnostic_text[-2400:]}"
            )
    return {"status": "PASS_LEGACY_APPLICATION_SMOKES", "commands": results}


def write_receipt(report: dict[str, Any]) -> pathlib.Path:
    REPORTS.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = REPORTS / f"LUNITA_TARGET_RUNTIME_ACCEPTANCE_{stamp}.json"
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("Short write while persisting target runtime receipt")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return path


def main() -> int:
    report: dict[str, Any] = {
        "schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_id": "G06_REBUILD_CANDIDATE_R1",
        "target": str(ROOT),
        "workflow_identity": workflow_identity_receipt(),
        "status": "BLOCKED",
        "certification": "NOT_GRANTED",
        "canonical_g06_certification": "NOT_GRANTED",
        "canonical_g08_binding_mutation": False,
    }
    try:
        report["xdg_runtime_dir"] = verify_xdg_runtime_dir()
        report["rootfs_build"] = verify_rootfs_build_receipt()
        overlay = verify_overlay()
        import engine_runtime_v1 as engine
        registry = engine.validate_registry()
        dependencies = engine.engine_dependency_inventory()
        if dependencies["status"] != "PASS":
            raise TargetGateError("Runtime dependencies are missing: " + ", ".join(dependencies["missing"]))
        report["overlay_integrity"] = overlay
        report["e04_quantization"] = verify_e04_quantization_receipt()
        report["engine_registry"] = registry
        report["dependency_inventory"] = dependencies
        report["qwen_e01"] = run_qwen_via_v18()
        report["engine_acceptance_tests"] = run_unittests()
        if report["engine_acceptance_tests"]["status"] != "PASS":
            raise TargetGateError("Engine acceptance suite failed or skipped tests")
        report["legacy_application_smokes"] = run_legacy_smokes()
        report["status"] = "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED"
    except Exception as exc:
        report["status"] = "BLOCKED_TARGET_RUNTIME_ACCEPTANCE"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)[:2400]}
    try:
        path = write_receipt(report)
        report["receipt_path"] = str(path)
        report["receipt_sha256"] = sha256_file(path)
    except Exception as exc:
        report["receipt_write_error"] = {"type": type(exc).__name__, "message": str(exc)[:1200]}
        report["status"] = "BLOCKED_TARGET_RUNTIME_ACCEPTANCE"
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
