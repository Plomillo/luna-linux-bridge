"""Evidence stays inside its root. A hash file is checked after it is written."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

from metagente_luna_s4.guard import require_case_id

_RUN = re.compile(r"run-[A-Za-z0-9._-]{1,80}")
_NAMES = {
    "instruction.json",
    "context.json",
    "ir.json",
    "plan.json",
    "fixture.json",
    "environment.json",
    "observed.json",
    "oracle.json",
    "metrics.json",
    "exit_code.json",
    "result.json",
}


def write_run(root: Path, case_id: str, run_id: str, documents: dict[str, dict]) -> Path:
    require_case_id(case_id)
    if not _RUN.fullmatch(run_id):
        raise ValueError("unsafe run id")
    if not documents or any(not isinstance(name, str) or name not in _NAMES for name in documents):
        raise ValueError("document name not allowed")
    base = Path(root).resolve()
    folder = (base / case_id / run_id).resolve()
    staging = (base / ".staging" / case_id / run_id).resolve()
    _contained(base, folder)
    _contained(base, staging)
    if folder.exists() or staging.exists():
        raise FileExistsError(run_id)
    staging.parent.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    try:
        sums = []
        for name, payload in documents.items():
            raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode()
            target = (staging / name).resolve()
            _contained(staging, target)
            target.write_bytes(raw)
            sums.append(f"{hashlib.sha256(raw).hexdigest()}  {name}")
        (staging / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        if verify_run(staging, base) != "EVIDENCE_VALIDATED":
            raise RuntimeError("evidence hash check failed before publication")
        folder.parent.mkdir(parents=True, exist_ok=True)
        os.rename(staging, folder)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return folder


def verify_run(folder: Path, root: Path) -> str:
    base = Path(root).resolve()
    target = Path(folder).resolve()
    try:
        _contained(base, target)
    except ValueError:
        return "EVIDENCE_REJECTED"
    manifest = target / "SHA256SUMS"
    if not manifest.is_file():
        return "EVIDENCE_INCOMPLETE"
    lines = [line for line in manifest.read_text(encoding="utf-8").splitlines() if line]
    if not lines:
        return "EVIDENCE_INCOMPLETE"
    for line in lines:
        digest, name = line.split("  ", 1)
        document = (target / name).resolve()
        try:
            _contained(target, document)
        except ValueError:
            return "EVIDENCE_REJECTED"
        if not document.is_file() or hashlib.sha256(document.read_bytes()).hexdigest() != digest:
            return "EVIDENCE_CORRUPTED"
    return "EVIDENCE_VALIDATED"


def _contained(root: Path, path: Path) -> None:
    if not path.is_relative_to(root):
        raise ValueError("path escapes the evidence root")
