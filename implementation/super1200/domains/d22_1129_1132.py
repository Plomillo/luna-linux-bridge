#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1129-1132. No certification."""
from __future__ import annotations

SPECS = {1129: ('MALWARE_TTP_KB',
        'KNOWLEDGE_BASE',
        'TTP IDs/definitions/sources/platforms/detection mappings'),
 1130: ('ATTACK_KNOWLEDGE_ADAPTER',
        'DATA_STANDARD_ADAPTER',
        'version/snapshot/provenance; ATT&CK AUTHORITY=NONE'),
 1131: ('IOC_KNOWLEDGE_BASE',
        'KNOWLEDGE_BASE',
        'indicator/type/source/first-last seen/confidence/expiry/context'),
 1132: ('IOC_EXPIRATION_ENGINE',
        'VALIDITY_ENGINE',
        'indicator freshness/repurposing/context; expired IOC retained historically but not '
        'active')}


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
