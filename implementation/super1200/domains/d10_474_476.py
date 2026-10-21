#!/usr/bin/env python3
"""D10 reviewed name-specific material for capabilities 474-476. No certification."""
from __future__ import annotations

SPECS = {474: ('ENGINE_COMPATIBILITY_GATE',
       'GATE',
       'interface/schema/platform/resource/provider compatibility and regression'),
 475: ('ENGINE_ROLLBACK_TEMPLATE',
       'TEMPLATE',
       'checkpoint, reversible changes, external side effects and verification oracles'),
 476: ('ENGINE_DOCUMENTATION_GENERATOR',
       'FACTORY_TOOL',
       'docs generated from manifest/contracts/tests to reduce drift')}


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
