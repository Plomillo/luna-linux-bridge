#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 917-920. No certification."""
from __future__ import annotations

SPECS = {917: ('DEPENDENCY_CONFUSION_DETECTOR',
       'SUPPLY_CHAIN_DETECTOR',
       'namespace/source precedence/private-public resolution verification'),
 918: ('PROVENANCE_SECURITY_GATE',
       'SECURITY_GATE',
       'unknown/untrusted origin increases risk; critical artifact requires sufficient provenance'),
 919: ('BUILD_INTEGRITY_SECURITY_GATE',
       'SECURITY_GATE',
       'artifact must match authorized source/build/toolchain/dependencies'),
 920: ('SUPPLY_CHAIN_INCIDENT_GRAPH',
       'INCIDENT_GRAPH',
       'compromised dependency→builds→artifacts→deployments→authorizations impact')}


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
