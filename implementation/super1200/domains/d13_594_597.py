#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 594-597. No certification."""
from __future__ import annotations

SPECS = {594: ('SKILL_GRAPH', 'GRAPH', 'skill prerequisite/composition/transfer edges'),
 595: ('MASTERY_CRITERIA_ENGINE', 'ASSESSMENT_POLICY', 'predeclared observable mastery thresholds'),
 596: ('FORMATIVE_ASSESSMENT_ENGINE',
       'ASSESSMENT_ENGINE',
       'item/rubric/result/error evidence used for adaptation, not certification'),
 597: ('SUMMATIVE_ASSESSMENT_ENGINE',
       'ASSESSMENT_ENGINE',
       'frozen rubric, coverage, scoring and audit trail')}


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
