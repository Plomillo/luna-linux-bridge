#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 785-788. No certification."""
from __future__ import annotations

SPECS = {785: ('REVERSE_DEPENDENCY_ANALYZER',
       'GRAPH_ANALYZER',
       'provider/capability/data consumers and impact reason paths'),
 786: ('AFFECTED_TEST_SELECTOR',
       'TEST_PLANNER',
       'map changes/claims to minimum sound test set; escalate when uncertain'),
 787: ('FULL_REGRESSION_ESCALATOR',
       'POLICY_ENGINE',
       'trigger full suite on high risk, graph uncertainty, core changes or evidence gaps'),
 788: ('REGRESSION_FIRST_POLICY',
       'POLICY',
       'new regressions prioritized and never silently accepted')}


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
