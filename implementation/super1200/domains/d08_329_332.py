#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 329-332. No certification."""
from __future__ import annotations

SPECS = {329: ('HISTORICAL_CLAIM_GRAPH', 'GRAPH', 'historical claims→sources→context→uncertainty'),
 330: ('ANACHRONISM_DETECTOR',
       'DOMAIN_VALIDATOR',
       'term/concept/time mismatch alerts, not automatic refutation'),
 331: ('COMPRESSION_FABRIC',
       'COMPRESSION_FABRIC',
       'classify/probe/benchmark/select, preserve integrity and partial-access requirements'),
 332: ('ARCHIVE_CLASSIFIER',
       'CLASSIFIER',
       'content/type/seekability/rebuildability before compression')}


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
