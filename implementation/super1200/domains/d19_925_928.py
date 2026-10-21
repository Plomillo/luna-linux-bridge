#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 925-928. No certification."""
from __future__ import annotations

SPECS = {925: ('CRITICAL_FILE_PROTECTION',
       'SECURITY_POLICY',
       'canonical/protected paths, allowed mutations, write detection and recovery refs'),
 926: ('PRIVILEGE_ESCALATION_MONITOR',
       'MONITOR',
       'identity/parent/action/authorization correlation; legitimate elevation distinguished'),
 927: ('SECURITY_EVENT_CORRELATOR',
       'CORRELATION_ENGINE',
       'time/host/object/causal grouping while retaining raw events'),
 928: ('NETWORK_SECURITY_FABRIC',
       'DEFENSIVE_SECURITY_FABRIC',
       'baseline/DNS/TLS/egress policy/anomaly correlation')}


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
