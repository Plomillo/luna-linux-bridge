#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1093-1096. No certification."""
from __future__ import annotations

SPECS = {1093: ('QUARANTINE_NETWORK_ESCAPE_TEST',
        'SECURITY_TEST',
        'verify deny-by-default egress and simulated-network containment'),
 1094: ('QUARANTINE_PRIVILEGE_TEST',
        'SECURITY_TEST',
        'verify no privilege gain across sandbox boundary'),
 1095: ('QUARANTINE_PERSISTENCE_TEST',
        'SECURITY_TEST',
        'verify sample state cannot persist beyond disposable environment'),
 1096: ('QUARANTINE_HOST_CONTAMINATION_TEST',
        'SECURITY_TEST',
        'before/after host filesystem/process/network baseline diff')}


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
