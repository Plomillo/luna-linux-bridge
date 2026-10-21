#!/usr/bin/env python3
"""D17 reviewed name-specific material for capabilities 753-756. No certification."""
from __future__ import annotations

SPECS = {753: ('ECOSYSTEM_FACTORY',
       'FACTORY',
       'namespace/contracts/providers/graphs/tests/docs without duplicating shared primitives'),
 754: ('COGNITIVE_UNIVERSE_FACTORY',
       'FACTORY',
       'new cognitive namespace/ontology/contracts with explicit interoperability'),
 755: ('METACOGNITIVE_UNIVERSE_FACTORY',
       'FACTORY',
       'new metacognitive namespace without authority drift'),
 756: ('ECOSYSTEM_INTEROPERABILITY_GATE',
       'GATE',
       'require typed inbound/outbound contracts and shared primitives')}


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
