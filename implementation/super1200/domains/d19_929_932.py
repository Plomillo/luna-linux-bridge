#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 929-932. No certification."""
from __future__ import annotations

SPECS = {929: ('NETWORK_BEHAVIOR_BASELINE',
       'BASELINE',
       'capability/process destinations/protocols/volumes/time patterns'),
 930: ('NETWORK_ANOMALY_DETECTOR',
       'DETECTOR',
       'deviation from per-capability/process baseline and policy'),
 931: ('DNS_SECURITY_ANALYZER',
       'DEFENSIVE_ANALYZER',
       'query/response/source/resolver/time anomalies and provenance'),
 932: ('TLS_SECURITY_ANALYZER',
       'DEFENSIVE_ANALYZER',
       'cert chain/protocol/cipher/hostname/time validity')}


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
