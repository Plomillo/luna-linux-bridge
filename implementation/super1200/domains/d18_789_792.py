#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 789-792. No certification."""
from __future__ import annotations

SPECS = {789: ('REGRESSION_REGISTRY',
       'REGISTRY',
       'regression ID/introduction/culprit/scope/tests/fix/status'),
 790: ('REGRESSION_BISECTION_ENGINE',
       'DIAGNOSTIC_ENGINE',
       'automated bounded bisection with reproducible test predicate'),
 791: ('SEMANTIC_DIFF_ENGINE',
       'DIFF_ENGINE',
       'distinguish formatting from identity/function/authority/meaning changes'),
 792: ('BEHAVIORAL_DIFF_ENGINE',
       'DIFF_ENGINE',
       'outputs/side effects/errors/performance/state transitions comparison')}


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
