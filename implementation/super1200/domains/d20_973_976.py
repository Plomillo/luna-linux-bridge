#!/usr/bin/env python3
"""D20 reviewed name-specific material for capabilities 973-976. No certification."""
from __future__ import annotations

SPECS = {973: ('STATIC_TRIAGE_ENGINE',
       'DEFENSIVE_ANALYZER',
       'identify type/metadata/signatures/active content without executing'),
 974: ('BEHAVIORAL_SANDBOX', 'SANDBOX', 'isolated controlled execution and full telemetry'),
 975: ('EPHEMERAL_ANALYSIS_VM',
       'VM_PROVIDER_PATTERN',
       'fresh snapshot per sample, disposable state, no shared secrets'),
 976: ('NETWORK_SIMULATION_SANDBOX',
       'SANDBOX',
       'simulated DNS/HTTP/etc without uncontrolled Internet')}


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
