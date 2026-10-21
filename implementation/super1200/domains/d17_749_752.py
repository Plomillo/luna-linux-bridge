#!/usr/bin/env python3
"""D17 reviewed name-specific material for capabilities 749-752. No certification."""
from __future__ import annotations

SPECS = {749: ('INTEREST_GRAPH',
       'KNOWLEDGE_GRAPH',
       'explicit user interests→projects/skills/resources; editable and non-diagnostic'),
 750: ('INTEREST_TO_COMPETENCY_ENGINE',
       'PLANNER',
       'interest→competency→prerequisite→practice/project path'),
 751: ('COMPETENCY_AMPLIFIER',
       'ORCHESTRATION_ENGINE',
       'combine pedagogy/tools/practice/projects and measure transfer'),
 752: ('PROJECT_INCUBATOR',
       'WORKFLOW_ENGINE',
       'idea→spec→risk→experiment→candidate→evidence→possible capability')}


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
