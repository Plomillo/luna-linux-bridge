#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1109-1112. No certification."""
from __future__ import annotations

SPECS = {1109: ('THREAT_KNOWLEDGE_PRESERVATION_GATE',
        'GATE',
        'required non-executable evidence/knowledge exists before destruction'),
 1110: ('NON_EXECUTABLE_THREAT_ARCHIVE',
        'KNOWLEDGE_STORE',
        'hashes/metadata/IOCs/behavior/rules only unless exceptional live-sample authorization'),
 1111: ('EXTERNAL_REFERENCE_ADAPTER',
        'INTELLIGENCE_ADAPTER',
        'external reference identity/date/source/confidence without copying hazardous material '
        'unnecessarily'),
 1112: ('THREAT_REACQUISITION_POLICY',
        'POLICY',
        'exceptional future reacquisition requires new need/risk/authorization')}


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
