"""One directory per run. Exit codes alone are not the record."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def write_run(root: Path, case_id: str, run_id: str, documents: dict[str, dict]) -> Path:
    folder = root / case_id / run_id
    folder.mkdir(parents=True, exist_ok=False)
    sums = []
    for name, payload in documents.items():
        raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode()
        (folder / name).write_bytes(raw)
        sums.append(f"{hashlib.sha256(raw).hexdigest()}  {name}")
    (folder / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return folder
