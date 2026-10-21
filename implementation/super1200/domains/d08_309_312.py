#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 309-312. No certification."""
from __future__ import annotations

SPECS = {309: ('CLAIM_SOURCE_QUALITY',
       'EVIDENCE_ENGINE',
       'source quality vector distinct from truth of claim'),
 310: ('EVIDENCE_TRIANGULATION',
       'EVIDENCE_ENGINE',
       'combine independent lines while preserving provenance and dependence'),
 311: ('SOURCE_INDEPENDENCE',
       'INDEPENDENCE_ENGINE',
       'citation/provenance ancestry graph detects copied/derived sources'),
 312: ('SOURCE_CONFLICT_RESOLUTION',
       'CONFLICT_ENGINE',
       'preserve conflicting sources; classify context/version before resolution')}


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
