#!/usr/bin/env python3
"""Persistent, bounded anti-paralysis journal for Cajita task planning.

This module records progress without storing request text. It never retries a
side-effecting operation by itself; retries require idempotency, known effects,
a verified checkpoint, and a finite attempt budget.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "CAJITA_ANTI_PARALYSIS_JOURNAL/1.0"
MAX_STAGNANT_OBSERVATIONS = 3
MAX_RETRY_ATTEMPTS = 3


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def retry_allowed(*, idempotent: bool, effect_known: bool, checkpoint_verified: bool,
                  attempts: int, deadline_expired: bool) -> bool:
    """Return a bounded decision; never execute or schedule a retry."""
    return bool(idempotent and effect_known and checkpoint_verified
                and 0 <= attempts < MAX_RETRY_ATTEMPTS and deadline_expired)


class PersistentAntiParalysis:
    def __init__(self, state_dir: str | Path):
        self.root = Path(state_dir).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink():
            raise RuntimeError("ANTI_PARALYSIS_STATE_ROOT_SYMLINK")
        self.journal = self.root / "events.jsonl"
        self.lock_path = self.root / ".journal.lock"
        self.tasks = self.root / "tasks"
        self.tasks.mkdir(exist_ok=True)

    @classmethod
    def default(cls) -> "PersistentAntiParalysis":
        base = os.environ.get("CAJITA_STATE_DIR")
        if base:
            return cls(Path(base) / "anti-paralysis")
        xdg = os.environ.get("XDG_STATE_HOME")
        parent = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "state"
        return cls(parent / "cajita" / "anti-paralysis")

    def _locked(self):
        """Bounded OS-level lock; lock contention fails closed instead of hanging."""
        class Lock:
            def __init__(self, path: Path):
                self.path = path
                self.fd = None
            def __enter__(self):
                self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
                try:
                    import time
                    deadline = time.monotonic() + 2.0
                    while True:
                        try:
                            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            return self
                        except BlockingIOError:
                            if time.monotonic() >= deadline:
                                raise RuntimeError("ANTI_PARALYSIS_LOCK_TIMEOUT")
                            time.sleep(0.025)
                except Exception:
                    os.close(self.fd)
                    self.fd = None
                    raise
            def __exit__(self, exc_type, exc, tb):
                if self.fd is not None:
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
                    os.close(self.fd)
                    self.fd = None
        return Lock(self.lock_path)

    def _read_chain(self) -> tuple[int, str]:
        if not self.journal.exists():
            return 0, "0" * 64
        previous = "0" * 64
        count = 0
        with self.journal.open("rb") as stream:
            for raw in stream:
                if not raw.endswith(b"\n"):
                    raise RuntimeError("ANTI_PARALYSIS_JOURNAL_TRUNCATED")
                try:
                    event = json.loads(raw)
                except Exception as exc:
                    raise RuntimeError("ANTI_PARALYSIS_JOURNAL_INVALID_JSON") from exc
                recorded = event.pop("event_sha256", None)
                if event.get("previous_sha256") != previous or recorded != digest_bytes(canonical_bytes(event)):
                    raise RuntimeError("ANTI_PARALYSIS_JOURNAL_CHAIN_INVALID")
                previous = recorded
                count += 1
        return count, previous

    def _append(self, payload: dict[str, Any]) -> str:
        count, previous = self._read_chain()
        event = dict(payload)
        event.update({"sequence": count + 1, "timestamp_utc": utc_now(), "previous_sha256": previous})
        event_hash = digest_bytes(canonical_bytes(event))
        event["event_sha256"] = event_hash
        fd = os.open(self.journal, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "ab", closefd=False) as stream:
                stream.write(canonical_bytes(event) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            os.close(fd)
        return event_hash

    def _task_file(self, task_id: str) -> Path:
        if not task_id or len(task_id) > 512:
            raise ValueError("ANTI_PARALYSIS_TASK_ID_INVALID")
        return self.tasks / (digest_bytes(task_id.encode("utf-8")) + ".json")

    def _save_task(self, path: Path, value: dict[str, Any]) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=".task-", dir=self.tasks)
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(canonical_bytes(value) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                tmp.unlink()

    def observe_plan(self, *, task_id: str, input_sha256: str, blockers: list[str],
                     plan_status: str) -> dict[str, Any]:
        if not valid_sha256(input_sha256):
            raise ValueError("ANTI_PARALYSIS_INPUT_SHA256_INVALID")
        clean_blockers = sorted(set(str(b)[:300] for b in blockers))
        blocked = bool(clean_blockers) or plan_status in {"FAIL_CLOSED", "PLAN_ONLY_BLOCKED"}
        blocker_digest = digest_bytes(canonical_bytes(clean_blockers))
        path = self._task_file(task_id)
        with self._locked():
            self._read_chain()  # Validate all prior evidence before changing state.
            prior = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            if prior and prior.get("input_sha256") != input_sha256:
                raise RuntimeError("ANTI_PARALYSIS_TASK_INPUT_COLLISION")
            if blocked:
                same_blocker = prior and prior.get("blocker_digest") == blocker_digest and prior.get("state") in {
                    "BLOCKED_WAITING_FOR_PREREQUISITES", "HOLD_CONSCIOUS"
                }
                stagnant = int(prior.get("stagnant_observations", 0)) + 1 if same_blocker else 1
                state = "HOLD_CONSCIOUS" if stagnant >= MAX_STAGNANT_OBSERVATIONS else "BLOCKED_WAITING_FOR_PREREQUISITES"
            else:
                stagnant = 0
                state = "PROGRESSING"
            record = {
                "schema": SCHEMA, "task_id_sha256": digest_bytes(task_id.encode("utf-8")),
                "input_sha256": input_sha256, "blocker_digest": blocker_digest,
                "blockers": clean_blockers, "stagnant_observations": stagnant,
                "max_stagnant_observations": MAX_STAGNANT_OBSERVATIONS,
                "retry_policy": "MAX_3; IDEMPOTENCY+KNOWN_EFFECT+VERIFIED_CHECKPOINT+EXPIRED_DEADLINE_REQUIRED",
                "state": state, "automatic_retry": False,
                "reason": "SAME_BLOCKERS_NO_FORWARD_PROGRESS" if blocked else "PLAN_PROGRESS_OBSERVED",
                "updated_at_utc": utc_now()
            }
            event_hash = self._append({"event": "PLAN_OBSERVED", "task_id_sha256": record["task_id_sha256"],
                                       "input_sha256": input_sha256, "state": state,
                                       "blocker_digest": blocker_digest,
                                       "stagnant_observations": stagnant})
            record["last_event_sha256"] = event_hash
            self._save_task(path, record)
            return {k: record[k] for k in (
                "state", "stagnant_observations", "max_stagnant_observations",
                "automatic_retry", "reason", "last_event_sha256"
            )}

    def status(self) -> dict[str, Any]:
        with self._locked():
            count, last_hash = self._read_chain()
            tasks = []
            for path in sorted(self.tasks.glob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                tasks.append({"task_id_sha256": data["task_id_sha256"], "state": data["state"],
                              "stagnant_observations": data["stagnant_observations"]})
            return {"schema": SCHEMA, "journal_events": count, "last_event_sha256": last_hash,
                    "task_count": len(tasks), "tasks": tasks,
                    "max_stagnant_observations": MAX_STAGNANT_OBSERVATIONS,
                    "automatic_retry": False, "status": "PASS"}

    @staticmethod
    def selftest() -> dict[str, Any]:
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix="cajita-antiparalysis-") as tmp:
            ctl = PersistentAntiParalysis(Path(tmp))
            task_id = "test-task"
            input_hash = digest_bytes(b"fixed-input")
            blockers = ["TASK_ADAPTER_NOT_REGISTERED"]
            results = [ctl.observe_plan(task_id=task_id, input_sha256=input_hash,
                                        blockers=blockers, plan_status="PLAN_ONLY_BLOCKED")
                       for _ in range(3)]
            status = ctl.status()
            assert [x["state"] for x in results] == [
                "BLOCKED_WAITING_FOR_PREREQUISITES",
                "BLOCKED_WAITING_FOR_PREREQUISITES",
                "HOLD_CONSCIOUS"
            ]
            assert status["journal_events"] == 3
            assert retry_allowed(idempotent=True, effect_known=True, checkpoint_verified=True,
                                 attempts=2, deadline_expired=True)
            assert not retry_allowed(idempotent=False, effect_known=True, checkpoint_verified=True,
                                     attempts=0, deadline_expired=True)
            return {"schema": SCHEMA, "status": "PASS", "bounded_stall_test": "PASS",
                    "journal_chain_test": "PASS", "retry_policy_test": "PASS",
                    "max_stagnant_observations": MAX_STAGNANT_OBSERVATIONS,
                    "automatic_retry": False}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("selftest", "status"))
    parser.add_argument("--state-dir")
    args = parser.parse_args()
    try:
        ctl = PersistentAntiParalysis(args.state_dir) if args.state_dir else PersistentAntiParalysis.default()
        result = PersistentAntiParalysis.selftest() if args.command == "selftest" else ctl.status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") == "PASS" else 2
    except Exception as exc:
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED",
                          "reason": type(exc).__name__ + ":" + str(exc)[:300]}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
