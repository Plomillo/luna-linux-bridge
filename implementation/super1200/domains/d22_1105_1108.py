#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1105-1108. No certification."""
from __future__ import annotations

SPECS = {1105: ('DESTRUCTION_RECEIPT',
        'RECEIPT',
        'sample ID/hash/locations/reason/authority/method/result'),
 1106: ('POST_DESTRUCTION_VERIFICATION',
        'VALIDATION_ENGINE',
        'verify governed locations/references no longer expose live sample'),
 1107: ('RESIDUAL_ARTIFACT_SCANNER',
        'DEFENSIVE_SCANNER',
        'search known hash/paths/components/indicators for unintended copies'),
 1108: ('REINFECTION_VECTOR_CHECK',
        'VALIDATION_ENGINE',
        'verify ingress/root-cause vector corrected after disposition')}


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
