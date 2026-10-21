#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 341-344. No certification."""
from __future__ import annotations

SPECS = {341: ('ZPAQ_PROVIDER', 'EXT_BINARY_TOOL', 'version/provenance and resource caps'),
 342: ('LONG_RANGE_COMPRESSION_PROVIDER',
       'PROVIDER_INTERFACE',
       'no provider selected without reproducibility/security/resource test'),
 343: ('DOMAIN_SPECIFIC_COMPRESSOR',
       'COMPRESSION_ENGINE',
       'domain contract, reversible transformation and fallback'),
 344: ('MODEL_WEIGHT_COMPRESSION',
       'DOMAIN_ENGINE',
       'model quality preserved via 229/230; not generic archive compression')}


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
