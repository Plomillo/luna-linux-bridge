#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 849-852. No certification."""
from __future__ import annotations

SPECS = {849: ('KNOWN_GOOD_GENERATION_REGISTRY',
       'REGISTRY',
       'complete known-good generation identity, roots, dependencies and evidence'),
 850: ('GENERATION_SWITCH_ENGINE',
       'RECOVERY_ENGINE',
       'atomic/controlled switch to known-good generation and live verification'),
 851: ('SAFE_GARBAGE_COLLECTION',
       'STORAGE_ENGINE',
       'reachability analysis; delete only unreferenced/unprotected objects'),
 852: ('ROLLBACK_ROOT_PROTECTION',
       'SAFETY_GATE',
       'GC/update/deprecation cannot delete required rollback roots')}


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
