#!/usr/bin/env python3
"""D20 reviewed name-specific material for capabilities 997-1000. No certification."""
from __future__ import annotations

SPECS = {997: ('DETECTION_RULE_SYNTHESIS',
       'RULE_FACTORY',
       'evidence patterns→candidate defensive rule; no automatic activation'),
 998: ('DETECTION_RULE_REGRESSION_LAB',
       'LAB',
       'historical benign/malicious corpus, fp/fn metrics and provider versions'),
 999: ('INCIDENT_REPLAY_ENGINE',
       'DEFENSIVE_SIMULATOR',
       'replay only necessary safe conditions/signals, no uncontrolled offensive execution'),
 1000: ('SECURITY_IMMUNE_MEMORY',
        'DEFENSIVE_KNOWLEDGE_MEMORY',
        'persistent incident/IOC/root-cause/fix/rule/prevention knowledge with expiry/provenance')}


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
