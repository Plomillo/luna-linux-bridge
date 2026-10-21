#!/usr/bin/env python3
"""D10 reviewed name-specific material for capabilities 466-469. No certification."""
from __future__ import annotations

SPECS = {466: ('ENGINE_ADAPTER_GENERATOR',
       'FACTORY_TOOL',
       'explicit source/target contract mappings and differential tests'),
 467: ('ENGINE_SANDBOX', 'SANDBOX', 'no-network/default least privilege, resource caps, teardown'),
 468: ('ENGINE_BENCHMARK_TEMPLATE',
       'TEMPLATE',
       'correctness/performance/resource/quality benchmark obligations'),
 469: ('ENGINE_PROVENANCE_TEMPLATE',
       'TEMPLATE',
       'source/build/tool/version/dependency/hash fields mandatory')}


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
