#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1017-1020. No certification."""
from __future__ import annotations

SPECS = {1017: ('HTML_SANITIZATION_ENGINE',
        'FORMAT_ENGINE',
        'remove executable/active constructs according to policy while preserving content'),
 1018: ('SCRIPT_SANITIZATION_ANALYZER',
        'ANALYZER',
        'determine recoverable legitimate source versus malicious modification; prefer clean '
        'rebuild'),
 1019: ('SOURCE_CODE_RECOVERY_ENGINE',
        'RECOVERY_ENGINE',
        'compare trusted source/history and rebuild legitimate code rather than patch unknown '
        'malware'),
 1020: ('BINARY_SANITIZATION_ANALYZER',
        'ANALYZER',
        'repair only if transform safety provable; otherwise trusted rebuild/substitution')}


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
