#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 555-558. No certification."""
from __future__ import annotations

SPECS = {555: ('C4_ARCHITECTURE_VIEWS',
       'DOCUMENTATION_VIEW',
       'views derived from architecture graph, not manually divergent source'),
 556: ('MACHINE_READABLE_ARCHITECTURE_DOCS',
       'DOCUMENTATION_ENGINE',
       'generate docs from schemas/graphs/manifests'),
 557: ('LIVE_DEPENDENCY_DIAGRAMS',
       'DOCUMENTATION_VIEW',
       'derived from current dependency graph with snapshot identity'),
 558: ('ARCHITECTURE_DRIFT_DOC_CHECK',
       'VALIDATION_ENGINE',
       'compare generated/declared docs to current graph/schema')}


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
