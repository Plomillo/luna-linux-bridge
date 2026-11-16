"""Single LUNITA mailbox. Consultas and Trabajos are modules, not agents."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from contracts_v1 import new_id

MODULES = {"CONSULTAS", "TRABAJOS"}
STATES = {
    "PENDING",
    "ACCEPTED",
    "RUNNING",
    "WAITING_FOR_INPUT",
    "WAITING_FOR_VALIDATION",
    "SUCCESS",
    "PARTIAL",
    "FAILED",
    "REJECTED",
    "TIMEOUT",
    "UNAVAILABLE",
    "VALIDATION_FAILED",
    "ROLLED_BACK",
}


class MailboxError(Exception):
    pass


class Mailbox:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def submit(self, module: str, text: str) -> dict:
        if module not in MODULES:
            raise MailboxError("UNKNOWN_MODULE")
        if not isinstance(text, str) or not text.strip():
            raise MailboxError("EMPTY_REQUEST")
        mission_id = new_id()
        record = {
            "mission_id": mission_id,
            "module": module,
            "text": text,
            "state": "ACCEPTED",
            "artifacts": [],
            "identity": "LUNITA",
            "brain_is_identity": False,
        }
        self._write(record)
        return record

    def attach_artifact(self, mission_id: str, path: Path) -> dict:
        record = self._read(mission_id)
        file_path = Path(path)
        if not file_path.is_file():
            raise MailboxError("ARTIFACT_MISSING")
        data = file_path.read_bytes()
        if not data:
            raise MailboxError("ARTIFACT_EMPTY")
        record["artifacts"].append(
            {
                "name": file_path.name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
        record["state"] = "WAITING_FOR_VALIDATION"
        self._write(record)
        return record

    def close(self, mission_id: str, state: str) -> dict:
        if state not in STATES:
            raise MailboxError("UNKNOWN_STATE")
        record = self._read(mission_id)
        if state == "SUCCESS" and not record["artifacts"]:
            record["state"] = "VALIDATION_FAILED"
            record["errors"] = ["SUCCESS_WITHOUT_ARTIFACT"]
            self._write(record)
            return record
        record["state"] = state
        self._write(record)
        return record

    def _path(self, mission_id: str) -> Path:
        return self.root / f"{mission_id}.json"

    def _write(self, record: dict) -> None:
        self._path(record["mission_id"]).write_text(
            json.dumps(record, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _read(self, mission_id: str) -> dict:
        path = self._path(mission_id)
        if not path.is_file():
            raise MailboxError("MISSION_NOT_FOUND")
        return json.loads(path.read_text(encoding="utf-8"))
