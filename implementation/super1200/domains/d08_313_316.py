#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 313-316. No certification."""
from __future__ import annotations

SPECS = {313: ('EPISTEMIC_STATUS_MACHINE',
       'STATE_MACHINE',
       'DECLARED→EVIDENCED→VALIDATED→INDEPENDENTLY_VALIDATED→CERTIFIED→ACTIVE; forbidden '
       'transitions executable'),
 314: ('HYPOTHESIS_REGISTRY',
       'REGISTRY',
       'hypothesis distinct from claim/fact; priors/assumptions/tests'),
 315: ('HYPOTHESIS_TESTING',
       'EVIDENCE_ENGINE',
       'predeclared discrimination criteria and results linked to hypotheses'),
 316: ('FALSIFICATION_RECORD', 'LEDGER', 'failed/refuting tests preserved, never discarded')}


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
