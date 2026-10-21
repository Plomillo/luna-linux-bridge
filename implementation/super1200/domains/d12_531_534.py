#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 531-534. No certification."""
from __future__ import annotations

SPECS = {531: ('CHAOS_ENGINEERING_FABRIC',
       'RESILIENCE_FABRIC',
       'authorized bounded experiments, blast radius, abort and recovery checkpoints'),
 532: ('FAULT_INJECTION', 'TEST_ENGINE', 'fault type/scope/duration/abort conditions recorded'),
 533: ('NETWORK_PARTITION_SIMULATOR',
       'SIMULATOR',
       'lab-only partition/latency/loss profiles and cleanup'),
 534: ('DISK_FAILURE_SIMULATOR',
       'SIMULATOR',
       'loopback/VM only; full/read-only/corruption scenarios')}


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
