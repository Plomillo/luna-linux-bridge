#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 517-520. No certification."""
from __future__ import annotations

SPECS = {517: ('DISCIPLINE_ONTOLOGY',
       'ONTOLOGY',
       'discipline identities, relations and scope; no authority conflation'),
 518: ('METHOD_ONTOLOGY',
       'ONTOLOGY',
       'method identity, assumptions, evidence outputs and constraints'),
 519: ('EVIDENCE_TYPE_ONTOLOGY',
       'ONTOLOGY',
       'evidence types by domain and admissibility/limitations'),
 520: ('CROSS_DISCIPLINE_TRANSLATOR',
       'SEMANTIC_ADAPTER',
       'concept mappings with non-equivalence/uncertainty explicit')}


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
