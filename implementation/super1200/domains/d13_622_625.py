#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 622-625. No certification."""
from __future__ import annotations

SPECS = {622: ('EXPLANATION_REGRESSION_TEST',
       'TEST_ENGINE',
       'factual/semantic assertions tied to machine-verifiable fixtures where possible'),
 623: ('PEDAGOGICAL_VERSIONING',
       'VERSIONING_POLICY',
       'material/objective/assessment version dependencies'),
 624: ('CURRICULUM_GRAPH',
       'GRAPH',
       'competencies/prerequisites/learning objects/assessments as DAG'),
 625: ('CURRICULUM_COMPILER',
       'PLANNER',
       'objective→prerequisite closure→learning sequence→assessment')}


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
