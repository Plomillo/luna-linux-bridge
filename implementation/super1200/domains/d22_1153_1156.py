#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1153-1156. No certification."""
from __future__ import annotations

SPECS = {1153: ('THREAT_KNOWLEDGE_LOCAL_CACHE',
        'CACHE',
        'offline snapshot with source/version/freshness and integrity'),
 1154: ('THREAT_KNOWLEDGE_INCREMENTAL_UPDATE',
        'UPDATE_ENGINE',
        'delta ingestion, source verification, conflict handling and rollback'),
 1155: ('THREAT_INTELLIGENCE_PROVENANCE',
        'PROVENANCE_ENGINE',
        'claim/source/date/feed/snapshot/transformation/confidence lineage'),
 1156: ('THREAT_INTELLIGENCE_CONFIDENCE',
        'EPISTEMIC_ENGINE',
        'confirmed/probable/contested/unknown tied to evidence quality and independence')}


def _bind(ctx, name: str, kind: str, hardening: str):
    if not isinstance(ctx, dict):
        return {"error": "missing_ctx"}
    claimed = ctx.get("canonical_name")
    if claimed not in (None, name):
        raise ValueError(f"identity mismatch for {name}")
    return {
        "binding": name.lower(),
        "kind": kind,
        "hardening": hardening,
        "status": "bound",
    }


def run(capability_id: int, ctx=None):
    if capability_id not in SPECS:
        raise ValueError(f"unregistered capability {capability_id}")
    name, kind, hardening = SPECS[capability_id]
    result = _bind(ctx, name, kind, hardening)
    result["canonical_name"] = name
    result["capability_id"] = capability_id
    result["certification_granted"] = False
    return result


FUNCS = {
    cid: (spec[0], (lambda ctx, cid=cid: run(cid, ctx)))
    for cid, spec in SPECS.items()
}
