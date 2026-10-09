"""Fail-closed budget reservation and telemetry API for Jonas.

This service does not invoke model providers. Callers must reserve before an
external call and settle from authoritative usage/billing evidence afterward.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

APP_VERSION = "0.1.0"
DB_PATH = os.environ.get("JONAS_DB_PATH", "./jonas-telemetry.sqlite3")
TOKEN = os.environ.get("JONAS_API_TOKEN", "")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

app = FastAPI(
    title="Jonas Budget & Telemetry API",
    version=APP_VERSION,
    description="Fail-closed reservation and telemetry only; no provider calls.",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def budget_config() -> tuple[int, int]:
    """Return (period limit, protected reserve), failing closed on bad config."""
    try:
        limit = int(os.environ["JONAS_PERIOD_LIMIT_MICRO_USD"])
        reserve = int(os.environ["JONAS_PROTECTED_RESERVE_MICRO_USD"])
    except (KeyError, ValueError):
        raise HTTPException(503, "Budget not explicitly configured; new calls are not authorized.")
    if limit <= 0 or reserve < 0 or reserve >= limit:
        raise HTTPException(503, "Invalid budget configuration; new calls are not authorized.")
    return limit, reserve


def require_auth(authorization: str | None = Header(default=None)) -> None:
    if not TOKEN:
        raise HTTPException(503, "JONAS_API_TOKEN is not configured.")
    expected = f"Bearer {TOKEN}"
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise HTTPException(401, "Unauthorized")


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        yield conn
    finally:
        conn.close()


def initialize_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS reservations (
          request_id TEXT PRIMARY KEY,
          estimated_micro_usd INTEGER NOT NULL CHECK (estimated_micro_usd > 0),
          actual_micro_usd INTEGER,
          model_id TEXT NOT NULL,
          policy_version TEXT NOT NULL,
          evidence_sha256 TEXT NOT NULL,
          status TEXT NOT NULL CHECK (status IN ('RESERVED','SETTLED','OVERRUN')),
          created_at_utc TEXT NOT NULL,
          settled_at_utc TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          event_at_utc TEXT NOT NULL,
          event_type TEXT NOT NULL,
          request_id TEXT,
          details_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS control_state (
          singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
          halted INTEGER NOT NULL,
          halt_reason TEXT,
          updated_at_utc TEXT NOT NULL
        );
        INSERT OR IGNORE INTO control_state(singleton, halted, halt_reason, updated_at_utc)
          VALUES(1, 0, NULL, CURRENT_TIMESTAMP);
        """)


def event(conn: sqlite3.Connection, event_type: str, request_id: str | None, details_json: str) -> None:
    conn.execute(
        "INSERT INTO events(event_at_utc,event_type,request_id,details_json) VALUES(?,?,?,?)",
        (utc_now(), event_type, request_id, details_json),
    )


@app.on_event("startup")
def startup() -> None:
    initialize_db()
    from .account_state import initialize_account_state_db
    initialize_account_state_db()


class ReservationRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    estimated_max_micro_usd: int = Field(gt=0)
    model_id: str = Field(min_length=1, max_length=160)
    policy_version: str = Field(min_length=1, max_length=80)
    evidence_sha256: str

    @field_validator("request_id")
    @classmethod
    def valid_request_id(cls, value: str) -> str:
        if not REQUEST_ID_RE.fullmatch(value):
            raise ValueError("request_id contains unsupported characters")
        return value

    @field_validator("evidence_sha256")
    @classmethod
    def valid_digest(cls, value: str) -> str:
        if not SHA256_RE.fullmatch(value):
            raise ValueError("evidence_sha256 must be a 64-character SHA-256 digest")
        return value.lower()


class SettlementRequest(BaseModel):
    actual_micro_usd: int = Field(ge=0)
    usage_evidence_sha256: str

    @field_validator("usage_evidence_sha256")
    @classmethod
    def valid_digest(cls, value: str) -> str:
        if not SHA256_RE.fullmatch(value):
            raise ValueError("usage_evidence_sha256 must be a 64-character SHA-256 digest")
        return value.lower()


class HaltRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


def spend_totals(conn: sqlite3.Connection) -> tuple[int, int]:
    row = conn.execute("""
      SELECT
        COALESCE(SUM(CASE WHEN status='RESERVED' THEN estimated_micro_usd ELSE 0 END),0) AS reserved,
        COALESCE(SUM(CASE WHEN status IN ('SETTLED','OVERRUN') THEN actual_micro_usd ELSE 0 END),0) AS settled
      FROM reservations
    """).fetchone()
    return int(row["reserved"]), int(row["settled"])


@app.get("/health")
def health() -> dict:
    return {"status": "process_alive", "version": APP_VERSION, "certified": False}


@app.post("/v1/reservations", dependencies=[Depends(require_auth)])
def create_reservation(payload: ReservationRequest) -> dict:
    limit, protected = budget_config()
    try:
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            state = conn.execute("SELECT halted, halt_reason FROM control_state WHERE singleton=1").fetchone()
            if state["halted"]:
                conn.rollback()
                raise HTTPException(423, "Jonas is halted; operator reconciliation is required.")
            old = conn.execute("SELECT * FROM reservations WHERE request_id=?", (payload.request_id,)).fetchone()
            if old:
                same = (
                    old["estimated_micro_usd"] == payload.estimated_max_micro_usd
                    and old["model_id"] == payload.model_id
                    and old["policy_version"] == payload.policy_version
                    and old["evidence_sha256"] == payload.evidence_sha256
                )
                conn.rollback()
                if not same:
                    raise HTTPException(409, "Idempotency conflict: request_id already exists with different parameters.")
                return {"request_id": old["request_id"], "status": old["status"], "idempotent_replay": True}
            reserved, settled = spend_totals(conn)
            spendable = limit - protected
            if settled + reserved + payload.estimated_max_micro_usd > spendable:
                event(conn, "RESERVATION_REJECTED", payload.request_id,
                      '{"reason":"insufficient_spendable_budget"}')
                conn.commit()
                raise HTTPException(402, "Insufficient spendable budget; protected reserve remains inaccessible.")
            conn.execute("""
              INSERT INTO reservations(request_id,estimated_micro_usd,model_id,policy_version,
                evidence_sha256,status,created_at_utc)
              VALUES(?,?,?,?,?,'RESERVED',?)
            """, (payload.request_id, payload.estimated_max_micro_usd, payload.model_id,
                  payload.policy_version, payload.evidence_sha256, utc_now()))
            event(conn, "RESERVATION_CREATED", payload.request_id,
                  '{"estimated_max_micro_usd":%d,"policy_version":"%s"}' %
                  (payload.estimated_max_micro_usd, payload.policy_version.replace('"', "")))
            conn.commit()
            return {
                "request_id": payload.request_id,
                "status": "RESERVED",
                "estimated_max_micro_usd": payload.estimated_max_micro_usd,
                "spendable_limit_micro_usd": spendable,
                "provider_call_performed": False,
            }
    except HTTPException:
        raise
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "Accounting unavailable; no new call is authorized.")


@app.post("/v1/reservations/{request_id}/settle", dependencies=[Depends(require_auth)])
def settle_reservation(request_id: str, payload: SettlementRequest) -> dict:
    try:
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM reservations WHERE request_id=?", (request_id,)).fetchone()
            if row is None:
                conn.rollback()
                raise HTTPException(404, "Reservation not found.")
            if row["status"] != "RESERVED":
                conn.rollback()
                if row["actual_micro_usd"] == payload.actual_micro_usd:
                    return {"request_id": request_id, "status": row["status"], "idempotent_replay": True}
                raise HTTPException(409, "Reservation already reconciled with different usage.")
            overrun = payload.actual_micro_usd > row["estimated_micro_usd"]
            status = "OVERRUN" if overrun else "SETTLED"
            conn.execute(
                "UPDATE reservations SET actual_micro_usd=?,status=?,settled_at_utc=? WHERE request_id=?",
                (payload.actual_micro_usd, status, utc_now(), request_id),
            )
            if overrun:
                conn.execute("UPDATE control_state SET halted=1,halt_reason=?,updated_at_utc=? WHERE singleton=1",
                             ("actual cost exceeded reserved upper bound", utc_now()))
            event(conn, "RESERVATION_OVERRUN" if overrun else "RESERVATION_SETTLED",
                  request_id, '{"actual_micro_usd":%d,"usage_evidence_sha256":"%s"}' %
                  (payload.actual_micro_usd, payload.usage_evidence_sha256))
            conn.commit()
            if overrun:
                raise HTTPException(409, "Actual cost exceeded reservation; ledger reconciled and new reservations halted.")
            return {"request_id": request_id, "status": status, "actual_micro_usd": payload.actual_micro_usd}
    except HTTPException:
        raise
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "Accounting unavailable; stop external calls and reconcile manually.")


@app.get("/v1/telemetry", dependencies=[Depends(require_auth)])
def telemetry() -> dict:
    try:
        limit, protected = budget_config()
        with db() as conn:
            reserved, settled = spend_totals(conn)
            state = conn.execute("SELECT halted,halt_reason,updated_at_utc FROM control_state WHERE singleton=1").fetchone()
            counts = conn.execute("SELECT status,COUNT(*) AS n FROM reservations GROUP BY status").fetchall()
            events = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
        return {
            "observed_at_utc": utc_now(),
            "period_limit_micro_usd": limit,
            "protected_reserve_micro_usd": protected,
            "spendable_limit_micro_usd": limit - protected,
            "reserved_micro_usd": reserved,
            "settled_micro_usd": settled,
            "remaining_spendable_micro_usd": limit - protected - reserved - settled,
            "halted": bool(state["halted"]),
            "halt_reason": state["halt_reason"],
            "halt_state_updated_at_utc": state["updated_at_utc"],
            "reservation_counts": {row["status"]: row["n"] for row in counts},
            "event_count": events,
            "prompts_recorded": False,
            "provider_billing_verified": False,
            "certified": False,
        }
    except HTTPException:
        raise
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "Telemetry/accounting unavailable; fail closed.")


@app.post("/v1/halt", dependencies=[Depends(require_auth)])
def halt(payload: HaltRequest) -> dict:
    try:
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE control_state SET halted=1,halt_reason=?,updated_at_utc=? WHERE singleton=1",
                         (payload.reason, utc_now()))
            event(conn, "OPERATOR_HALT", None, '{"reason_sha256":"%s"}' %
                  hashlib.sha256(payload.reason.encode()).hexdigest())
            conn.commit()
        return {"halted": True, "reason_recorded_as_hash": True}
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "Cannot verify durable halt state; isolate the caller and stop external calls.")


@app.post("/v1/resume", dependencies=[Depends(require_auth)])
def resume(payload: HaltRequest) -> dict:
    """Explicit operator action. Caller is responsible for reconciliation before use."""
    try:
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE control_state SET halted=0,halt_reason=NULL,updated_at_utc=? WHERE singleton=1",
                         (utc_now(),))
            event(conn, "OPERATOR_RESUME", None, '{"operator_attestation_sha256":"%s"}' %
                  hashlib.sha256(payload.reason.encode()).hexdigest())
            conn.commit()
        return {"halted": False, "warning": "Operator attestation recorded; this API cannot independently prove reconciliation."}
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "Cannot verify durable resume state.")


# Additive shared account-credit and model-catalog ledger.
from .account_state import router as account_state_router
app.include_router(account_state_router)
