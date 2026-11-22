"""Shared run context. No expected answers."""
from __future__ import annotations

import os
from pathlib import Path


def discover_repo() -> Path:
    env = os.environ.get("LOUKSNA_REPO", "")
    if env and Path(env).is_dir():
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "louksna" / "session" / "src" / "mra.rs").is_file():
            return parent
    return Path("/tmp/luna-linux-bridge")


class Ctx:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def d(self, n: int) -> Path:
        path = self.root / f"case-{n:03d}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def repo(self) -> Path:
        return discover_repo()

    @property
    def session_bin(self) -> str:
        env = os.environ.get("LOUKSNA_SESSION_BIN", "")
        if env:
            return env
        candidate = self.repo / "louksna" / "session" / "target" / "release" / "louksna-session"
        if candidate.is_file():
            return str(candidate)
        return "/tmp/luna-linux-bridge/louksna/session/target/release/louksna-session"
