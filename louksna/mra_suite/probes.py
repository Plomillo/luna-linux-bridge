"""Environment probes. Copied logic may live in the oracle; do not import this from oracle modules."""
from __future__ import annotations

import os
from pathlib import Path


def os_version_id() -> str:
    text = Path("/etc/os-release").read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if line.startswith("VERSION_ID="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


def wayland_real() -> bool:
    if os.environ.get("XDG_SESSION_TYPE") != "wayland":
        return False
    display = os.environ.get("WAYLAND_DISPLAY", "")
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    if not display or not runtime:
        return False
    return Path(runtime, display).exists()


def kde_real() -> bool:
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "") + os.environ.get("DESKTOP_SESSION", "")
    if "KDE" not in desktop.upper():
        return False
    return Path("/usr/bin/plasmashell").exists() or Path("/usr/bin/startplasma-wayland").exists()


def corpus_dir() -> str:
    return os.environ.get("LOUKSNA_CORPUS_DIR", "")


def xai_configured() -> bool:
    if os.environ.get("LOUKSNA_XAI_API_KEY"):
        return True
    home = Path(os.environ.get("HOME", "/root"))
    return (home / ".local/share/louksna/secrets/xai_api_key").is_file()
