#!/usr/bin/env python3
"""Run a command as the ordinary louksna user, with the Plasma session environment if it exists."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys


def session_env() -> dict[str, str]:
    env = os.environ.copy()
    uid = subprocess.check_output(["id", "-u", "louksna"], text=True).strip()
    env["HOME"] = "/home/louksna"
    env["USER"] = "louksna"
    env["LOGNAME"] = "louksna"
    env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
    proc = pathlib.Path("/proc")
    for pid in proc.iterdir():
        if not pid.name.isdigit():
            continue
        try:
            cmd = (pid / "cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        except OSError:
            continue
        if "plasmashell" not in cmd:
            continue
        try:
            raw = (pid / "environ").read_bytes().split(b"\x00")
        except OSError:
            break
        for item in raw:
            if b"=" not in item:
                continue
            key, value = item.split(b"=", 1)
            name = key.decode(errors="replace")
            if name in {
                "WAYLAND_DISPLAY",
                "XDG_RUNTIME_DIR",
                "XDG_SESSION_TYPE",
                "XDG_CURRENT_DESKTOP",
                "DESKTOP_SESSION",
                "DBUS_SESSION_BUS_ADDRESS",
                "DISPLAY",
                "QT_QPA_PLATFORM",
            }:
                env[name] = value.decode(errors="replace")
        break
    return env


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: as_session.py command...", file=sys.stderr)
        return 2
    env = session_env()
    os.execvpe("runuser", ["runuser", "-u", "louksna", "--preserve-environment", "--", *sys.argv[1:]], env)


if __name__ == "__main__":
    raise SystemExit(main())
