#!/usr/bin/env python3
"""Remove only a verified dead Chromium smoke-test singleton socket.

Chromium's Linux ProcessSingleton creates a 0700 temporary directory containing
SingletonSocket and, when present, SingletonCookie. SingletonCookie is companion
metadata, not a socket, and is never authorized for deletion. This cleanup
unlinks only a dead, non-symlink Unix socket that belongs to the expected user
and is not registered in the supplied live-socket table. Every other entry is
preserved. The directory is removed only when that socket was its sole entry.
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
COOKIE_NAME = "SingletonCookie"
COOKIE_UINT64_MAX = (1 << 64) - 1


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


def validated_cookie_target(cookie_path: pathlib.Path, *, expected_uid: int) -> tuple[str, os.stat_result]:
    """Validate Chromium's remote SingletonCookie symlink without following it."""
    if not cookie_path.is_symlink():
        raise CleanupError(f"Chromium companion cookie is not a symlink: {cookie_path}")
    cookie_stat = cookie_path.lstat()
    if cookie_stat.st_uid != expected_uid:
        raise CleanupError(
            f"Chromium companion cookie owner mismatch at {cookie_path}: "
            f"expected uid {expected_uid}, found {cookie_stat.st_uid}"
        )
    try:
        target = os.readlink(cookie_path)
    except OSError as exc:
        raise CleanupError(f"Cannot inspect Chromium companion cookie {cookie_path}: {exc}") from exc
    if (
        not target.isascii()
        or not target.isdigit()
        or len(target) > 20
        or str(int(target)) != target
        or int(target) > COOKIE_UINT64_MAX
    ):
        raise CleanupError(f"Chromium companion cookie has an invalid uint64 token: {cookie_path}")
    return target, cookie_stat


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
        if directory_stat.st_uid != expected_uid:
            raise CleanupError(
                f"Chromium temporary directory owner mismatch at {directory}: "
                f"expected uid {expected_uid}, found {directory_stat.st_uid}"
            )
        directory_mode = stat.S_IMODE(directory_stat.st_mode)
        if directory_mode != 0o700:
            raise CleanupError(
                f"Chromium temporary directory mode mismatch at {directory}: "
                f"expected 0o700, found {oct(directory_mode)}"
            )
        try:
            children = list(directory.iterdir())
        except OSError as exc:
            raise CleanupError(f"Cannot inspect Chromium temporary directory {directory}: {exc}") from exc
        names = {child.name for child in children}
        if names not in ({SOCKET_NAME}, {SOCKET_NAME, COOKIE_NAME}):
            raise CleanupError(
                f"Refusing to remove non-canonical Chromium temp data at {directory}; "
                f"entries={sorted(names)!r}"
            )
        sock = directory / SOCKET_NAME
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
        cookie_path = directory / COOKIE_NAME if COOKIE_NAME in names else None
        cookie_target = None
        cookie_stat = None
        if cookie_path is not None:
            cookie_target, cookie_stat = validated_cookie_target(cookie_path, expected_uid=expected_uid)
        guest_socket_path = f"/tmp/{directory.name}/{SOCKET_NAME}"
        if guest_socket_path in registered:
            raise CleanupError(f"Chromium singleton socket is still registered as live: {guest_socket_path}")
        candidates.append({
            "directory": directory,
            "directory_stat": directory_stat,
            "directory_mode": directory_mode,
            "socket": sock,
            "socket_stat": socket_stat,
            "cookie": cookie_path,
            "cookie_target": cookie_target,
            "cookie_stat": cookie_stat,
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
    # Validation is complete before the first unlink; no recursive deletion is used.
    for candidate in candidates:
        sock = candidate["socket"]
        directory = candidate["directory"]
        original_dir = candidate["directory_stat"]
        current_dir = directory.lstat()
        if (
            not stat.S_ISDIR(current_dir.st_mode)
            or current_dir.st_dev != original_dir.st_dev
            or current_dir.st_ino != original_dir.st_ino
            or current_dir.st_uid != expected_uid
            or stat.S_IMODE(current_dir.st_mode) != 0o700
        ):
            raise CleanupError(f"Chromium temporary directory changed after preflight: {directory}")
        expected_names = {SOCKET_NAME}
        if candidate["cookie"] is not None:
            expected_names.add(COOKIE_NAME)
        current_names = {item.name for item in directory.iterdir()}
        if current_names != expected_names:
            raise CleanupError(
                f"Chromium temporary directory contents changed after preflight: "
                f"{directory}; entries={sorted(current_names)!r}"
            )
        original_socket = candidate["socket_stat"]
        current_socket = sock.lstat()
        if (
            not stat.S_ISSOCK(current_socket.st_mode)
            or current_socket.st_uid != expected_uid
            or current_socket.st_dev != original_socket.st_dev
            or current_socket.st_ino != original_socket.st_ino
        ):
            raise CleanupError(f"Chromium singleton socket changed after preflight: {sock}")
        if candidate["guest_socket_path"] in registered_unix_sockets(proc_net_unix):
            raise CleanupError(
                f"Chromium singleton socket became live after preflight: {candidate['guest_socket_path']}"
            )
        cookie_path = candidate["cookie"]
        if cookie_path is not None:
            original_cookie = candidate["cookie_stat"]
            current_cookie = cookie_path.lstat()
            if (
                not stat.S_ISLNK(current_cookie.st_mode)
                or current_cookie.st_uid != expected_uid
                or current_cookie.st_dev != original_cookie.st_dev
                or current_cookie.st_ino != original_cookie.st_ino
                or os.readlink(cookie_path) != candidate["cookie_target"]
            ):
                raise CleanupError(f"Chromium companion cookie changed after preflight: {cookie_path}")
        sock.unlink()
        remaining = sorted(item.name for item in directory.iterdir())
        directory_removed = False
        if not remaining:
            directory.rmdir()
            directory_removed = True
        elif set(remaining) != ({COOKIE_NAME} if cookie_path is not None else set()):
            raise CleanupError(
                f"Chromium temporary directory retained unexpected entries after socket removal: "
                f"{directory}; entries={remaining!r}"
            )
        removed.append({
            "path": candidate["guest_socket_path"],
            "uid": candidate["uid"],
            "gid": candidate["gid"],
            "mode_octal": candidate["mode_octal"],
            "companion_cookie_symlink_removed": False,
            "companion_cookie_preserved": cookie_path is not None,
            "directory_removed": directory_removed,
            "preserved_entries": remaining,
            "status": "REMOVED_DEAD_TEST_SOCKET",
        })
    return {
        "schema": SCHEMA,
        "status": "PASS_TRANSIENT_CHROMIUM_CLEANUP",
        "rootfs_tmp": "/tmp",
        "expected_socket_owner_uid": expected_uid,
        "removed_count": len(removed),
        "removed": removed,
        "policy": "REMOVE_ONLY_DEAD_DIRECT_0700_SINGLETONSOCKET;PRESERVE_SINGLETONCOOKIE_AND_ALL_OTHER_ENTRIES;NO_RECURSIVE_DELETE",
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
        os.chmod(dead_dir, 0o700)
        dead_socket = dead_dir / SOCKET_NAME
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(dead_socket))
        listener.close()
        result = cleanup(rootfs, expected_uid=owner, proc_net_unix=fake_proc)
        if result["removed_count"] != 1 or dead_dir.exists() or dead_socket.exists():
            raise CleanupError("Self-test failed to remove exactly one dead Chromium singleton socket")

        extra_dir = tmp / f"{PREFIX}extra"
        extra_dir.mkdir()
        os.chmod(extra_dir, 0o700)
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

        cookie_dir = tmp / f"{PREFIX}cookie"
        cookie_dir.mkdir()
        os.chmod(cookie_dir, 0o700)
        cookie_socket = cookie_dir / SOCKET_NAME
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(cookie_socket))
        listener.close()
        cookie_link = cookie_dir / COOKIE_NAME
        cookie_link.symlink_to("18446744073709551615")
        cookie_result = cleanup(rootfs, expected_uid=owner, proc_net_unix=fake_proc)
        if (
            cookie_result["removed_count"] != 1
            or not cookie_dir.exists()
            or cookie_socket.exists()
            or not cookie_link.is_symlink()
            or os.readlink(cookie_link) != "18446744073709551615"
            or cookie_result["removed"][0]["companion_cookie_symlink_removed"] is not False
            or cookie_result["removed"][0]["companion_cookie_preserved"] is not True
            or cookie_result["removed"][0]["directory_removed"] is not False
            or cookie_result["removed"][0]["preserved_entries"] != [COOKIE_NAME]
        ):
            raise CleanupError("Self-test failed to remove only the dead socket while preserving SingletonCookie")
        shutil.rmtree(cookie_dir)

        unsafe_cookie_dir = tmp / f"{PREFIX}unsafe-cookie"
        unsafe_cookie_dir.mkdir()
        os.chmod(unsafe_cookie_dir, 0o700)
        unsafe_cookie_socket = unsafe_cookie_dir / SOCKET_NAME
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(unsafe_cookie_socket))
        listener.close()
        unsafe_cookie = unsafe_cookie_dir / COOKIE_NAME
        unsafe_cookie.symlink_to("../../etc/passwd")
        try:
            cleanup(rootfs, expected_uid=owner, proc_net_unix=fake_proc)
        except CleanupError:
            pass
        else:
            raise CleanupError("Self-test failed to reject a non-numeric Chromium companion cookie")
        if not unsafe_cookie_socket.exists() or not unsafe_cookie.is_symlink():
            raise CleanupError("Self-test modified a Chromium directory with an invalid companion cookie")
        shutil.rmtree(unsafe_cookie_dir)

        live_dir = tmp / f"{PREFIX}live"
        live_dir.mkdir()
        os.chmod(live_dir, 0o700)
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
        shutil.rmtree(live_dir)
        fake_proc.write_text("Num RefCount Protocol Flags Type St Inode Path\n", encoding="utf-8")

        missing = base / "missing-rootfs"
        try:
            cleanup(missing, expected_uid=owner, proc_net_unix=fake_proc)
        except CleanupError:
            pass
        else:
            raise CleanupError("Self-test failed to reject a missing rootfs")

        outside = tmp / "not-chromium"
        outside.mkdir()
        outside_socket = outside / SOCKET_NAME
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(outside_socket))
        listener.close()
        kept = cleanup(rootfs, expected_uid=owner, proc_net_unix=fake_proc)
        if kept["removed_count"] != 0 or not outside_socket.exists():
            raise CleanupError("Self-test removed a socket outside the Chromium temp prefix")
        shutil.rmtree(outside)

        link_dir = tmp / f"{PREFIX}link"
        link_target = base / "outside-temp"
        link_target.mkdir()
        (link_target / "secret").write_text("preserve", encoding="utf-8")
        link_dir.symlink_to(link_target, target_is_directory=True)
        try:
            cleanup(rootfs, expected_uid=owner, proc_net_unix=fake_proc)
        except CleanupError:
            pass
        else:
            raise CleanupError("Self-test failed to reject a Chromium path that is a symlink")
        if not (link_target / "secret").exists():
            raise CleanupError("Self-test followed a symlink and modified data outside the temp directory")
        link_dir.unlink()

        locked = tmp / f"{PREFIX}locked"
        locked.mkdir()
        os.chmod(locked, 0o700)
        locked_socket = locked / SOCKET_NAME
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(locked_socket))
        listener.close()
        os.chmod(locked, 0o000)
        try:
            try:
                cleanup(rootfs, expected_uid=owner, proc_net_unix=fake_proc)
            except CleanupError:
                pass
            else:
                raise CleanupError("Self-test failed to reject a Chromium directory that cannot be inspected")
        finally:
            os.chmod(locked, 0o700)
        if not locked_socket.exists():
            raise CleanupError("Self-test removed a socket from a directory that could not be inspected")
        shutil.rmtree(locked)
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
