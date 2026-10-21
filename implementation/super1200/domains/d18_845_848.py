#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 845-848. No certification."""
from __future__ import annotations

SPECS = {845: ('CAUSAL_CACHE_INVALIDATION',
       'INVALIDATION_ENGINE',
       'dependency/evidence graph decides invalidation'),
 846: ('TEST_RESULT_REUSE_ENGINE',
       'EVIDENCE_REUSE_ENGINE',
       'reuse only exact test code/input/env/tool/policy identities'),
 847: ('BUILD_RESULT_REUSE_ENGINE',
       'CACHE_ENGINE',
       'reuse only exact content/toolchain/build config keys'),
 848: ('DIAGNOSTIC_RESULT_REUSE',
       'KNOWLEDGE_REUSE_ENGINE',
       'same symptoms insufficient; state/version/root-cause preconditions must match')}


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
