#!/usr/bin/env python3
"""Root-owned GLOBAL one-use register for a future independently governed executor.

Not a root broker and not an authority: merely burns a fully scoped, externally
verified operation ONCE before a separate, reviewed executor can consider it.
No CLI, no arbitrary shell, no key issuance and no access through the read-only
remote gateway. Deployment requires owner consent and new independent gates.
"""
from __future__ import annotations
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

import external_gates

SCHEMA = "LRB_GLOBAL_SCOPE_CONSUMPTION/0.1"
DEFAULT_ROOT = Path("/var/lib/louksna/remote-bridge")
HASH = re.compile(r"^[a-f0-9]{64}$")
SCOPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
ROLES = ("G23", "G24", "G23_2", "G24_2")


def _protected_root(root):
    if os.geteuid() != 0:
        raise RuntimeError("ROOT_BROKER_ONLY_NO_REMOTE_CALL")
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise RuntimeError("ROOT_GLOBAL_REGISTRY_MISSING")
    for parent in (root, *root.parents):
        if parent == Path("/"):
            continue
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise RuntimeError("UNPROTECTED_GLOBAL_REGISTRY_PARENT")
    info = root.stat()
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise RuntimeError("GLOBAL_REGISTRY_MUST_BE_0700")


def _pinned_file(root):
    db = root / "GLOBAL_SCOPE.db"
    if db.is_symlink():
        raise RuntimeError("GLOBAL_SCOPE_DB_SYMLINK_DENIED")
    if db.exists():
        info = db.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise RuntimeError("GLOBAL_SCOPE_DB_UNPROTECTED")
    else:
        fd = os.open(db, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        os.chmod(db, 0o600)
    return db


class GlobalScopeRegister:
    def __init__(self, root=DEFAULT_ROOT):
        self.root = Path(root)

    def _connection(self):
        _protected_root(self.root)
        db = _pinned_file(self.root)
        connection = sqlite3.connect(str(db), isolation_level=None, timeout=5)
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("""CREATE TABLE IF NOT EXISTS once (
            scope_id TEXT PRIMARY KEY NOT NULL,
            request_sha256 TEXT NOT NULL UNIQUE,
            mission_sha256 TEXT NOT NULL UNIQUE,
            operation_sha256 TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            host TEXT NOT NULL,
            boot_id TEXT NOT NULL,
            receipt_sha256 TEXT NOT NULL,
            disposition TEXT NOT NULL CHECK(disposition='CONSUMED_NO_DISPATCH')
        )""")
        return connection

    def consume(self, *, request_path, owner_signature, receipts,
                verifier, expected_host, expected_boot,
                source_path, operation_sha256):
        """Global first-wins, fail-closed before any material root dispatch.

        Re-verifies ALL signed gates *inside* the database's exclusive write
        transaction; a crash after commit intentionally burns the scope. The
        executor must separately verify the signed operation and cannot infer
        permission from this return value.
        """
        if set(receipts) != set(ROLES) or not all(
            isinstance(receipts[k], dict) and set(receipts[k]) == {"document","signature"}
            for k in ROLES):
            raise RuntimeError("ALL_INDEPENDENT_SECOND_ORDER_RECEIPTS_REQUIRED")
        raw = external_gates.read_regular(request_path)
        request = json.loads(raw)
        scope = request.get("scope_id")
        if not isinstance(scope, str) or not SCOPE.fullmatch(scope):
            raise RuntimeError("INVALID_GLOBAL_SCOPE_ID")
        if not isinstance(operation_sha256, str) or not HASH.fullmatch(operation_sha256):
            raise RuntimeError("EXACT_OPERATION_DIGEST_REQUIRED")
        if request.get("operation_sha256") != operation_sha256:
            raise RuntimeError("SIGNED_OPERATION_IDENTITY_MISMATCH")
        if not Path(source_path).is_file() or Path(source_path).is_symlink():
            raise RuntimeError("LIVE_SOURCE_NOT_PINNED")
        source_sha256 = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
        if (request.get("source_sha256") != source_sha256
                or request.get("host") != expected_host
                or request.get("boot_id") != expected_boot
                or not isinstance(request.get("mission_sha256"), str)
                or not HASH.fullmatch(request["mission_sha256"])):
            raise RuntimeError("SIGNED_EXECUTION_SCOPE_DRIFT")
        request_sha256 = hashlib.sha256(raw).hexdigest()
        with closing(self._connection()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                exists = db.execute(
                    "SELECT 1 FROM once WHERE scope_id=? OR request_sha256=? OR mission_sha256=?",
                    (scope, request_sha256, request["mission_sha256"])).fetchone()
                if exists:
                    raise RuntimeError("GLOBAL_SCOPE_REPLAY_OR_MISSION_DUPLICATION")
                report = verifier.preflight(request_path, owner_signature, receipts,
                    strong=True, expected_host=expected_host, expected_boot=expected_boot)
                if (report.get("status") != "SIGNED_RECEIPTS_CRYPTOGRAPHICALLY_VERIFIED"
                        or report.get("scope_id") != scope
                        or report.get("host") != expected_host
                        or report.get("boot_id") != expected_boot
                        or report.get("capability") != request.get("capability")
                        or report.get("strong_second_order_receipts_verified") is not True
                        or report.get("execution_authorized_by_this_verifier") is not False
                        or report.get("certified") is not False
                        or not isinstance(report.get("hashes"), dict)
                        or report["hashes"].get("request_sha256") != request_sha256
                        or not all(isinstance(report["hashes"].get(k), str)
                            and HASH.fullmatch(report["hashes"][k]) for k in
                            ("g23_sha256","g24_sha256","g23_2_sha256","g24_2_sha256"))):
                    raise RuntimeError("GLOBAL_GATE_REPORT_UNTRUSTED")
                receipt_sha256 = hashlib.sha256(json.dumps(
                    report["hashes"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
                db.execute("INSERT INTO once VALUES(?,?,?,?,?,?,?,?,?)",
                    (scope,request_sha256,request["mission_sha256"],operation_sha256,
                     source_sha256,expected_host,expected_boot,receipt_sha256,
                     "CONSUMED_NO_DISPATCH"))
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise
        return {"schema":SCHEMA, "status":"CONSUMED_NO_DISPATCH",
                "scope_id":scope,"request_sha256":request_sha256,
                "receipt_sha256":receipt_sha256,
                "privileged_dispatch_performed":False,
                "owner_and_issuer_independence_certified":False,
                "execution_authorized_by_registry":False,"certified":False}
