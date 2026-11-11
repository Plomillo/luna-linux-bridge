#!/usr/bin/env python3
"""Remove only dead, uniquely identified Chromium smoke-test singleton sockets.

This is a narrow pre-packaging cleanup. Unknown files, live sockets, symlinks,
wrong owners, and unexpected directory contents are rejected without mutation.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import socket
import stat
import tempfile
from datetime import datetime, timezone
from typing import Any

SCHEMA = "LUNITA_ROOTFS_TRANSIENT_BROWSER_CLEANUP/1.0"
PREFIX = "org.chromium.Chromium."
SOCKET_NAME = "SingletonSocket"


class CleanupError(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def registered_unix_sockets(proc_net_unix: pathlib.Path) -> set[str]:
    try:
        lines = proc_net_unix.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CleanupError(f"Cannot inspect live Unix sockets at {proc_net_unix}: {exc}") from exc
    registered: set[str] = set()
    for line in lines[1:]:
        fields = line.split()
        if len(fields) >= 8 and fields[-1].startswith("/"):
            registered.add(fields[-1])
    return registered


def inspect_candidates(
    rootfs: pathlib.Path,
    *,
    expected_uid: int,
    proc_net_unix: pathlib.Path,
) -> list[dict[str, Any]]:
    if rootfs.is_symlink() or not rootfs.is_dir():
        raise CleanupError(f"Rootfs must be a real directory: {rootfs}")
    tmp = rootfs / "tmp"
    if tmp.is_symlink() or not tmp.is_dir():
        raise CleanupError(f"Rootfs /tmp is missing or unsafe: {tmp}")
    registered = registered_unix_sockets(proc_net_unix)
    candidates: list[dict[str, Any]] = []
    for directory in sorted(tmp.iterdir(), key=lambda item: item.name):
        if not directory.name.startswith(PREFIX):
            continue
        if directory.parent != tmp or directory.is_symlink():
            raise CleanupError(f"Chromium temporary path is not a direct, real /tmp directory: {directory}")
        directory_stat = directory.lstat()
        if not stat.S_ISDIR(directory_stat.st_mode):
            raise CleanupError(f"Chromium temporary path is not a directory: {directory}")
        try:
            children = list(directory.iterdir())
        except OSError as exc:
            raise CleanupError(f"Cannot inspect Chromium temporary directory {directory}: {exc}") from exc
        if len(children) != 1 or children[0].name != SOCKET_NAME:
            names = sorted(child.name for child in children)
            raise CleanupError(
                f"Refusing to remove non-socket Chromium temp data at {directory}; entries={names!r}"
            )
        sock = children[0]
        if sock.is_symlink():
            raise CleanupError(f"Chromium singleton socket path is a symlink: {sock}")
        socket_stat = sock.lstat()
        if not stat.S_ISSOCK(socket_stat.st_mode):
            raise CleanupError(f"Chromium singleton path is not a Unix socket: {sock}")
        if socket_stat.st_uid != expected_uid:
            raise CleanupError(
                f"Chromium singleton socket owner mismatch at {sock}: "
                f"expected uid {expected_uid}, found {socket_stat.st_uid}"
            )
        guest_socket_path = f"/tmp/{directory.name}/{SOCKET_NAME}"
        if guest_socket_path in registered:
            raise CleanupError(f"Chromium singleton socket is still registered as live: {guest_socket_path}")
        candidates.append({
            "directory": directory,
            "socket": sock,
            "guest_socket_path": guest_socket_path,
            "uid": socket_stat.st_uid,
            "gid": socket_stat.st_gid,
            "mode_octal": oct(stat.S_IMODE(socket_stat.st_mode)),
        })
    return candidates


def cleanup(
    rootfs: pathlib.Path,
    *,
    expected_uid: int,
    proc_net_unix: pathlib.Path = pathlib.Path("/proc/net/unix"),
) -> dict[str, Any]:
    rootfs = pathlib.Path(os.path.abspath(rootfs))
    candidates = inspect_candidates(rootfs, expected_uid=expected_uid, proc_net_unix=proc_net_unix)
    removed: list[dict[str, Any]] = []
    # Validation is complete before the first unlink; rmdir refuses unexpected new entries.
    for candidate in candidates:
        sock = candidate["socket"]
        directory = candidate["directory"]
        current = sock.lstat()
        if not stat.S_ISSOCK(current.st_mode) or current.st_uid != expected_uid:
            raise CleanupError(f"Chromium singleton socket changed after preflight: {sock}")
        if directory.is_symlink() or not directory.is_dir():
            raise CleanupError(f"Chromium temporary directory changed after preflight: {directory}")
        sock.unlink()
        directory.rmdir()
        removed.append({
            "path": candidate["guest_socket_path"],
            "uid": candidate["uid"],
            "gid": candidate["gid"],
            "mode_octal": candidate["mode_octal"],
            "status": "REMOVED_DEAD_TEST_SOCKET",
        })
    return {
        "schema": SCHEMA,
        "status": "PASS_TRANSIENT_CHROMIUM_CLEANUP",
        "rootfs_tmp": "/tmp",
        "expected_socket_owner_uid": expected_uid,
        "removed_count": len(removed),
        "removed": removed,
        "policy": "ONLY_DIRECT_ORG_CHROMIUM_DIR_WITH_SINGLE_DEAD_SINGLETONSOCKET;NO_RECURSIVE_DELETE",
        "certification": "NOT_GRANTED",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def write_receipt(path: pathlib.Path, record: dict[str, Any]) -> None:
    path = pathlib.Path(os.path.abspath(path))
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise CleanupError(f"Receipt parent directory is missing or unsafe: {path.parent}")
    if path.exists() or path.is_symlink():
        raise CleanupError(f"Refusing to overwrite cleanup receipt: {path}")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        payload = canonical_json(record)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="lunita-chrome-cleanup-selftest-") as temporary:
        base = pathlib.Path(temporary)
        rootfs = base / "rootfs"
        tmp = rootfs / "tmp"
        tmp.mkdir(parents=True)
        fake_proc = base / "proc-net-unix"
        fake_proc.write_text("Num RefCount Protocol Flags Type St Inode Path\n", encoding="utf-8")
        owner = os.getuid()

        dead_dir = tmp / f"{PREFIX}dead"
        dead_dir.mkdir()
        dead_socket = dead_dir / SOCKET_NAME
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(dead_socket))
        listener.close()
        result = cleanup(rootfs, expected_uid=owner, proc_net_unix=fake_proc)
        if result["removed_count"] != 1 or dead_dir.exists() or dead_socket.exists():
            raise CleanupError("Self-test failed to remove exactly one dead Chromium singleton socket")

        extra_dir = tmp / f"{PREFIX}extra"
        extra_dir.mkdir()
        extra_socket = extra_dir / SOCKET_NAME
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(extra_socket))
        listener.close()
        extra_file = extra_dir / "unexpected-data"
        extra_file.write_text("preserve me", encoding="utf-8")
        try:
            cleanup(rootfs, expected_uid=owner, proc_net_unix=fake_proc)
        except CleanupError:
            pass
        else:
            raise CleanupError("Self-test failed to reject a Chromium temp directory with additional data")
        if not extra_socket.exists() or not extra_file.exists():
            raise CleanupError("Self-test modified data in a rejected Chromium temp directory")

        shutil.rmtree(extra_dir)
        live_dir = tmp / f"{PREFIX}live"
        live_dir.mkdir()
        live_socket = live_dir / SOCKET_NAME
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(live_socket))
        socket_path = f"/tmp/{live_dir.name}/{SOCKET_NAME}"
        fake_proc.write_text(
            "Num RefCount Protocol Flags Type St Inode Path\n"
            f"0000000000000000: 00000002 00000000 00010000 0001 01 999 {socket_path}\n",
            encoding="utf-8",
        )
        try:
            cleanup(rootfs, expected_uid=owner, proc_net_unix=fake_proc)
        except CleanupError:
            pass
        else:
            raise CleanupError("Self-test failed to reject a still-registered Unix socket")
        if not live_socket.exists():
            raise CleanupError("Self-test removed a socket that was still registered as live")
        listener.close()
    print("PASS_TRANSIENT_CHROMIUM_CLEANUP_SELF_TEST")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    clean = sub.add_parser("clean")
    clean.add_argument("--rootfs", type=pathlib.Path, required=True)
    clean.add_argument("--expected-uid", type=int, default=1000)
    clean.add_argument("--proc-net-unix", type=pathlib.Path, default=pathlib.Path("/proc/net/unix"))
    clean.add_argument("--receipt", type=pathlib.Path, required=True)
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "clean":
        record = cleanup(args.rootfs, expected_uid=args.expected_uid, proc_net_unix=args.proc_net_unix)
        write_receipt(args.receipt, record)
        print(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
