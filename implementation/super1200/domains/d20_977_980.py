#!/usr/bin/env python3
"""D20 reviewed name-specific material for capabilities 977-980. No certification."""
from __future__ import annotations

SPECS = {977: ('FILESYSTEM_BEHAVIOR_RECORDER',
       'FORENSIC_RECORDER',
       'record read/write/create/delete paths/time/process'),
 978: ('PROCESS_BEHAVIOR_RECORDER', 'FORENSIC_RECORDER', 'process tree/exec/IPC/privilege/time'),
 979: ('PERSISTENCE_BEHAVIOR_RECORDER',
       'FORENSIC_RECORDER',
       'record persistence attempts without permitting host persistence'),
 980: ('BEHAVIOR_TIMELINE',
       'FORENSIC_TIMELINE',
       'event/observed/recorded timestamps and causal uncertainty')}


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
