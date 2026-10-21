#!/usr/bin/env python3
"""D20 reviewed name-specific material for capabilities 965-968. No certification."""
from __future__ import annotations

SPECS = {965: ('QUARANTINE_ACCESS_CONTROL',
       'SECURITY_POLICY',
       'least privilege analyzer-only access and audited retrieval'),
 966: ('QUARANTINE_NETWORK_ISOLATION',
       'SECURITY_BOUNDARY',
       'default-deny network with simulated endpoints when needed'),
 967: ('QUARANTINE_EXECUTION_ISOLATION',
       'SECURITY_BOUNDARY',
       'no direct host execution; disposable sandbox only'),
 968: ('QUARANTINE_EVIDENCE_PRESERVATION',
       'EVIDENCE_ENGINE',
       'raw bytes/hash/metadata/source/detection preserved before transforms')}


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
