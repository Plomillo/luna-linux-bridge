#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1101-1104. No certification."""
from __future__ import annotations

SPECS = {1101: ('SAMPLE_RELEASE_PROHIBITION',
        'SECURITY_POLICY',
        'confirmed malicious sample cannot return to operational paths'),
 1102: ('THREAT_DESTRUCTION_GATE',
        'SECURITY_GATE',
        'destruction only after identity/evidence/knowledge retention/authorization prerequisites'),
 1103: ('THREAT_DESTRUCTION_AUTHORIZATION',
        'AUTHORIZATION_CONTROL',
        'destructive authority separate from detector/analyzer and scope to exact sample hash'),
 1104: ('SECURE_SAMPLE_DISPOSAL',
        'REMEDIATION_ENGINE',
        'remove governed stored copy according to storage medium guarantees; no exaggerated '
        'secure-erasure claim')}


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
