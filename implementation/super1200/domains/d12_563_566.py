#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 563-566. No certification."""
from __future__ import annotations

SPECS = {563: ('SCHEMA_COMPATIBILITY',
       'VALIDATION_ENGINE',
       'backward/forward/full compatibility rules per schema family'),
 564: ('API_VERSIONING',
       'API_POLICY',
       'version semantics, deprecation, coexistence and migration path'),
 565: ('API_CONTRACT_TESTING', 'TEST_ENGINE', 'provider/consumer conformance against exact spec'),
 566: ('API_FUZZING',
       'TEST_ENGINE',
       'schema-aware generated inputs, resource caps and reproducible crashes')}


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
