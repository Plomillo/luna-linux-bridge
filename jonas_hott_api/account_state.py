"""Shared 1min.AI account-credit observations and model-catalog snapshots.

A credit balance is only as authoritative as its source. This module never
infers account credits from token usage. It supports manually observed balances
now; an official balance API must be verified before any automatic sync is added.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from . import app as app_module
from .app import SHA256_RE, require_auth, utc_now

router = APIRouter(tags=["shared-account-state"])


def _db() -> sqlite3.Connection:
    Path(app_module.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(app_module.DB_PATH, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def initialize_account_state_db() -> None:
    with _db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS credit_observations (
          observation_id TEXT PRIMARY KEY,
          observed_at_utc TEXT NOT NULL,
          recorded_at_utc TEXT NOT NULL,
          balance_credits INTEGER NOT NULL CHECK(balance_credits >= 0),
          source_kind TEXT NOT NULL CHECK(source_kind IN ('manual','official_api')),
          source_reference TEXT NOT NULL,
          actor TEXT NOT NULL,
          evidence_sha256 TEXT NOT NULL,
          notes TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS model_catalog_snapshots (
          snapshot_id TEXT PRIMARY KEY,
          observed_at_utc TEXT NOT NULL,
          recorded_at_utc TEXT NOT NULL,
          source_kind TEXT NOT NULL CHECK(source_kind IN ('manual','official_api')),
          source_reference TEXT NOT NULL,
          actor TEXT NOT NULL,
          models_json TEXT NOT NULL,
          evidence_sha256 TEXT NOT NULL
        );
        """)


def _require_digest(value: str) -> str:
    if not SHA256_RE.fullmatch(value):
        raise ValueError("evidence_sha256 must be a 64-character SHA-256 digest")
    return value.lower()


class CreditObservation(BaseModel):
    observation_id: str = Field(min_length=1, max_length=128)
    observed_at_utc: str = Field(min_length=20, max_length=40)
    balance_credits: int = Field(ge=0)
    source_kind: Literal["manual", "official_api"]
    source_reference: str = Field(min_length=1, max_length=500)
    actor: str = Field(min_length=1, max_length=120)
    evidence_sha256: str
    notes: str = Field(default="", max_length=1000)

    @field_validator("observed_at_utc")
    @classmethod
    def valid_utc_timestamp(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("observed_at_utc must be ISO-8601 with timezone") from exc
        if parsed.tzinfo is None:
            raise ValueError("observed_at_utc must include a timezone")
        return parsed.astimezone(timezone.utc).isoformat()

    @field_validator("evidence_sha256")
    @classmethod
    def valid_evidence_digest(cls, value: str) -> str:
        return _require_digest(value)


class CatalogModel(BaseModel):
    model_id: str = Field(min_length=1, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    capabilities: list[str] = Field(default_factory=list, max_length=40)
    metadata: dict = Field(default_factory=dict)


class CatalogSnapshot(BaseModel):
    snapshot_id: str = Field(min_length=1, max_length=128)
    observed_at_utc: str = Field(min_length=20, max_length=40)
    source_kind: Literal["manual", "official_api"]
    source_reference: str = Field(min_length=1, max_length=500)
    actor: str = Field(min_length=1, max_length=120)
    models: list[CatalogModel] = Field(min_length=1, max_length=1000)
    evidence_sha256: str

    @field_validator("observed_at_utc")
    @classmethod
    def valid_utc_timestamp(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("observed_at_utc must be ISO-8601 with timezone") from exc
        if parsed.tzinfo is None:
            raise ValueError("observed_at_utc must include a timezone")
        return parsed.astimezone(timezone.utc).isoformat()

    @field_validator("evidence_sha256")
    @classmethod
    def valid_evidence_digest(cls, value: str) -> str:
        return _require_digest(value)


def _freshness(observed_at_utc: str) -> dict:
    observed = datetime.fromisoformat(observed_at_utc.replace("Z", "+00:00"))
    age_seconds = max(0, int((datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()))
    try:
        ttl = int(os.environ.get("JONAS_ACCOUNT_STATE_TTL_SECONDS", "3600"))
    except ValueError:
        ttl = 0
    fresh = ttl > 0 and age_seconds <= ttl
    return {
        "freshness": "FRESH" if fresh else "STALE",
        "age_seconds": age_seconds,
        "ttl_seconds": ttl,
    }


@router.post("/v1/account/credits/observations", dependencies=[Depends(require_auth)])
def record_credit_observation(payload: CreditObservation) -> dict:
    """Append an observation. It does not claim automatic provider synchronization."""
    try:
        with _db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            old = conn.execute(
                "SELECT * FROM credit_observations WHERE observation_id=?",
                (payload.observation_id,),
            ).fetchone()
            if old:
                same = (
                    old["balance_credits"] == payload.balance_credits
                    and old["source_kind"] == payload.source_kind
                    and old["source_reference"] == payload.source_reference
                    and old["evidence_sha256"] == payload.evidence_sha256
                )
                conn.rollback()
                if not same:
                    raise HTTPException(409, "Observation ID conflict; history is append-only.")
                return {"observation_id": payload.observation_id, "idempotent_replay": True}
            conn.execute("""
                INSERT INTO credit_observations
                (observation_id, observed_at_utc, recorded_at_utc, balance_credits,
                 source_kind, source_reference, actor, evidence_sha256, notes)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                payload.observation_id, payload.observed_at_utc, utc_now(),
                payload.balance_credits, payload.source_kind, payload.source_reference,
                payload.actor, payload.evidence_sha256, payload.notes,
            ))
            conn.commit()
        return {"observation_id": payload.observation_id, "recorded": True, "history_mutated": False}
    except HTTPException:
        raise
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "Shared account-state ledger unavailable; observation not accepted.")


@router.get("/v1/account/credits", dependencies=[Depends(require_auth)])
def latest_credit_observation() -> dict:
    try:
        with _db() as conn:
            row = conn.execute("""
                SELECT * FROM credit_observations
                ORDER BY observed_at_utc DESC, recorded_at_utc DESC LIMIT 1
            """).fetchone()
        if row is None:
            return {"status": "UNKNOWN", "balance_credits": None, "certified": False}
        result = dict(row)
        result.update(_freshness(row["observed_at_utc"]))
        result["status"] = "OBSERVED"
        result["balance_is_estimate"] = False
        result["certified"] = False
        return result
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "Shared account-state ledger unavailable; balance is unknown.")


@router.get("/v1/account/credits/history", dependencies=[Depends(require_auth)])
def credit_observation_history(limit: int = Query(default=100, ge=1, le=1000)) -> dict:
    try:
        with _db() as conn:
            rows = conn.execute("""
                SELECT * FROM credit_observations
                ORDER BY recorded_at_utc DESC LIMIT ?
            """, (limit,)).fetchall()
        return {"observations": [dict(row) for row in rows], "append_only": True}
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "Shared account-state history unavailable.")


@router.post("/v1/models/catalog/snapshots", dependencies=[Depends(require_auth)])
def record_model_catalog(payload: CatalogSnapshot) -> dict:
    """Persist a sourced catalog snapshot; caller must not label estimates as official."""
    canonical = json.dumps(
        [model.model_dump(mode="json") for model in payload.models],
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    computed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    try:
        with _db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            old = conn.execute(
                "SELECT evidence_sha256 FROM model_catalog_snapshots WHERE snapshot_id=?",
                (payload.snapshot_id,),
            ).fetchone()
            if old:
                conn.rollback()
                if old["evidence_sha256"] != payload.evidence_sha256:
                    raise HTTPException(409, "Catalog snapshot ID conflict.")
                return {"snapshot_id": payload.snapshot_id, "idempotent_replay": True}
            conn.execute("""
                INSERT INTO model_catalog_snapshots
                (snapshot_id, observed_at_utc, recorded_at_utc, source_kind,
                 source_reference, actor, models_json, evidence_sha256)
                VALUES(?,?,?,?,?,?,?,?)
            """, (
                payload.snapshot_id, payload.observed_at_utc, utc_now(),
                payload.source_kind, payload.source_reference, payload.actor,
                canonical, payload.evidence_sha256,
            ))
            conn.commit()
        return {
            "snapshot_id": payload.snapshot_id,
            "model_count": len(payload.models),
            "canonical_catalog_sha256": computed,
            "recorded": True,
            "provider_catalog_verified": payload.source_kind == "official_api",
            "certified": False,
        }
    except HTTPException:
        raise
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "Model catalog ledger unavailable; snapshot not accepted.")


@router.get("/v1/models/catalog", dependencies=[Depends(require_auth)])
def latest_model_catalog() -> dict:
    try:
        with _db() as conn:
            row = conn.execute("""
                SELECT * FROM model_catalog_snapshots
                ORDER BY observed_at_utc DESC, recorded_at_utc DESC LIMIT 1
            """).fetchone()
        if row is None:
            return {"status": "UNKNOWN", "models": [], "certified": False}
        result = dict(row)
        result["models"] = json.loads(result.pop("models_json"))
        result.update(_freshness(row["observed_at_utc"]))
        result["status"] = "OBSERVED"
        result["certified"] = False
        return result
    except (sqlite3.Error, OSError, json.JSONDecodeError):
        raise HTTPException(503, "Shared model catalog unavailable.")
