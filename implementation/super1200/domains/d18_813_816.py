#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 813-816. No certification."""
from __future__ import annotations

SPECS = {813: ('SCHEMA_EVOLUTION_ENGINE',
       'SCHEMA_ENGINE',
       'versioned migrations, unknown/default behavior and round-trip tests'),
 814: ('DATA_MIGRATION_ENGINE',
       'MIGRATION_ENGINE',
       'idempotent versioned migration with source/target hashes and checkpoints'),
 815: ('MIGRATION_PREFLIGHT',
       'GATE',
       'compatibility/space/resources/locks/backup/deps before write'),
 816: ('MIGRATION_DRY_RUN',
       'SIMULATION_ENGINE',
       'execute plan against copy/transaction without commit')}


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
