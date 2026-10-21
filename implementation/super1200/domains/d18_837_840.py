#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 837-840. No certification."""
from __future__ import annotations

SPECS = {837: ('UPDATE_FREEZE_PROTECTION',
       'SECURITY_ENGINE',
       'detect stale metadata/channel freeze while respecting authorized pins'),
 838: ('UPDATE_ROLLBACK_ATTACK_PROTECTION',
       'SECURITY_ENGINE',
       'reject malicious older versions unless explicit recovery authorization'),
 839: ('UPDATE_PROVENANCE_GATE',
       'SECURITY_GATE',
       'source/signature/attestation/SBOM/build identity before update'),
 840: ('UPDATE_CERTIFICATION_GATE',
       'ASSURANCE_GATE',
       'determine evidence/G23/G24 invalidated by update; certification never auto-updates')}


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
