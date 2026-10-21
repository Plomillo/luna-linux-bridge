#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 793-796. No certification."""
from __future__ import annotations

SPECS = {793: ('CONFIGURATION_DIFF_ENGINE', 'DIFF_ENGINE', 'typed semantic config changes and defaults'),
 794: ('DEPENDENCY_DIFF_ENGINE',
       'DIFF_ENGINE',
       'direct/transitive/version/source/license/security dependency changes'),
 795: ('ABI_DIFF_ENGINE', 'DIFF_ENGINE', 'symbol/layout/calling convention compatibility'),
 796: ('API_DIFF_ENGINE', 'DIFF_ENGINE', 'endpoint/message/schema/semantic contract changes')}


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
