#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 295-298. No certification."""
from __future__ import annotations

SPECS = {295: ('GROUNDED_THEORY_WORKFLOW',
       'WORKFLOW',
       'iterative coding/memo/sampling stages explicit; no false method claim'),
 296: ('INTERCODER_RELIABILITY',
       'VALIDATION_ENGINE',
       'agreement metric, sample, coder independence and limitations'),
 297: ('AUDIT_TRAIL_QUALITATIVE',
       'AUDIT_LEDGER',
       'append-only interpretive decisions and evidence refs'),
 298: ('MEMOING_SYSTEM', 'KNOWLEDGE_STORE', 'versioned memos linked to evidence/codes and author')}


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
