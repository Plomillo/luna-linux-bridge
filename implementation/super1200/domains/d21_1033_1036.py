#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1033-1036. No certification."""
from __future__ import annotations

SPECS = {1033: ('MULTI_ENGINE_RESCAN',
        'VALIDATION_ENGINE',
        'independent scanners/rules with versions and disagreement preservation'),
 1034: ('FALSE_SANITIZATION_DETECTOR',
        'DETECTOR',
        'detect residual active/malicious behavior or semantic break despite apparent clean '
        'result'),
 1035: ('INFORMATION_EXTRACTION_FALLBACK',
        'RECOVERY_ENGINE',
        'extract only demonstrably safe information when full artifact cannot be recovered'),
 1036: ('SAFE_FORMAT_TRANSCODER',
        'FORMAT_ENGINE',
        'convert to less-active format with semantic preservation and new identity')}


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
