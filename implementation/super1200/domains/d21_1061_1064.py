#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1061-1064. No certification."""
from __future__ import annotations

SPECS = {1061: ('SUBSTITUTE_FUNCTIONAL_TEST', 'TEST_ENGINE', 'utility contract conformance'),
 1062: ('SUBSTITUTE_COMPATIBILITY_TEST',
        'TEST_ENGINE',
        'consumer/API/schema/platform compatibility'),
 1063: ('SUBSTITUTE_PERFORMANCE_TEST',
        'BENCHMARK',
        'matched latency/throughput comparison to requirements'),
 1064: ('SUBSTITUTE_RESOURCE_TEST', 'BENCHMARK', 'CPU/RAM/disk/network against resource envelope')}


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
