"""Shared run context. No expected answers."""
from __future__ import annotations

import os
from pathlib import Path


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
        return Path(os.environ.get("LOUKSNA_REPO", "/tmp/luna-linux-bridge"))

    @property
    def session_bin(self) -> str:
        return os.environ.get(
            "LOUKSNA_SESSION_BIN",
            "/tmp/luna-linux-bridge/louksna/session/target/release/louksna-session",
        )
