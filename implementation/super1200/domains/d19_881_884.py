#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 881-884. No certification."""
from __future__ import annotations

SPECS = {881: ('MALWARE_DEFENSE_FABRIC',
       'DEFENSIVE_SECURITY_FABRIC',
       'multi-signal defensive detection with containment, evidence and false-positive controls'),
 882: ('SIGNATURE_SCANNER_INTERFACE',
       'PROVIDER_INTERFACE',
       'scan file/stream with engine/db version/result/evidence'),
 883: ('CLAMAV_PROVIDER',
       'EXT_SECURITY_ENGINE',
       'engine/db versions, update provenance, resource limits; AUTHORITY=NONE'),
 884: ('YARA_PROVIDER',
       'EXT_SECURITY_LIBRARY_TOOL',
       'engine/rule-set versions, compiled rules and provenance')}


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
