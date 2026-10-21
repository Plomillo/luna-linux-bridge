#!/usr/bin/env python3
"""D10 reviewed name-specific material for capabilities 454-457. No certification."""
from __future__ import annotations

SPECS = {454: ('LSP_FACTORY', 'FACTORY', 'protocol/version, parser/type integration and fixture tests'),
 455: ('FORMATTER_FACTORY', 'FACTORY', 'idempotent formatting and syntax-preservation tests'),
 456: ('DEBUGGER_PROTOCOL_PROVIDER',
       'PROVIDER_INTERFACE',
       'debug protocol scope, auth if remote and target isolation'),
 457: ('PACKAGE_MANAGER_FACTORY',
       'FACTORY',
       'package identity, dependency solver, lockfile, signatures/provenance and rollback')}


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
