#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 897-900. No certification."""
from __future__ import annotations

SPECS = {897: ('PERSISTENCE_DETECTOR',
       'DETECTOR',
       'services/tasks/autoruns/systemd/registry etc mapped to baseline and authorization'),
 898: ('MALICIOUS_BEHAVIOR_GRAPH',
       'GRAPH',
       'behavior nodes/causal relations/evidence/time and confidence'),
 899: ('MALWARE_FAMILY_CLASSIFIER',
       'CLASSIFIER',
       'family/variant similarity with confidence; unknown family allowed'),
 900: ('MALWARE_ANALYSIS_RECEIPT',
       'RECEIPT',
       'object hash/tools/db/rules/environment/findings/classification/limitations')}


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
