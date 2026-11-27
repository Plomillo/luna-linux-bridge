"""Fail closed if the pinned protocol or the pinned program is missing."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def check(root: Path) -> dict:
    lock_path = root / "mission" / "manifests" / "MISSION_INPUTS.lock.json"
    if not lock_path.is_file():
        return {"ok": False, "reason": "LOCK_MISSING"}
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    checked = []
    for doc in lock["documents"]:
        path = root / doc["path_in_worktree"]
        if not path.is_file():
            return {"ok": False, "reason": "SOURCE_MISSING", "path": doc["path_in_worktree"]}
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != doc["sha256"]:
            return {"ok": False, "reason": "SOURCE_HASH_MISMATCH", "path": doc["path_in_worktree"], "actual": digest}
        checked.append(doc["role"])
    return {"ok": True, "reason": "SOURCES_PINNED", "checked": checked}


def main(argv: list[str] | None = None) -> int:
    root = Path(sys.argv[1] if argv is None and len(sys.argv) > 1 else (argv[0] if argv else "."))
    result = check(root)
    sys.stdout.write(json.dumps(result) + "\n")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
