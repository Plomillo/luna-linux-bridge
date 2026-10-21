#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 921-924. No certification."""
from __future__ import annotations

SPECS = {921: ('HOST_INTRUSION_DETECTION_FABRIC',
       'DEFENSIVE_SECURITY_FABRIC',
       'baseline→events→anomaly→correlation→evidence→containment authorization'),
 922: ('PROCESS_BEHAVIOR_BASELINE',
       'BASELINE',
       'process identity,parent,exec,path,user,network/files patterns per machine/capability'),
 923: ('PROCESS_ANOMALY_DETECTOR',
       'DETECTOR',
       'deviations from baseline with confidence and context'),
 924: ('FILESYSTEM_INTEGRITY_MONITOR',
       'MONITOR',
       'protected paths/hash/metadata/expected writers and event loss handling')}


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
