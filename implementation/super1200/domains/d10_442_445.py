#!/usr/bin/env python3
"""D10 reviewed name-specific material for capabilities 442-445. No certification."""
from __future__ import annotations

SPECS = {442: ('AST_SCHEMA', 'SCHEMA', 'node identity/version/source spans and backwards compatibility'),
 443: ('SEMANTIC_ANALYZER',
       'LANGUAGE_ENGINE',
       'name/type/scope rules and deterministic diagnostics'),
 444: ('TYPE_SYSTEM_FACTORY', 'FACTORY', 'type rules/formal properties/conformance tests'),
 445: ('DEPENDENT_TYPE_LANGUAGE_LAB',
       'LAB',
       'experimental only until semantics/proofs/tooling mature')}


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
