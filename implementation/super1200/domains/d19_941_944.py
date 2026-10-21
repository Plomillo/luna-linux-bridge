#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 941-944. No certification."""
from __future__ import annotations

SPECS = {941: ('LUNA_DEFENDER',
       'DEFENSIVE_SECURITY_SYSTEM',
       'orchestrator over existing security primitives, not monolithic scanner'),
 942: ('LUNA_DEFENDER_RULE_ENGINE',
       'RULE_ENGINE',
       'versioned rules, provenance, scope, test status and rollback'),
 943: ('LUNA_DEFENDER_BEHAVIOR_ENGINE',
       'DEFENSIVE_ENGINE',
       'consume behavioral analyzers/host/network signals, no duplicate telemetry'),
 944: ('LUNA_DEFENDER_REPUTATION_ENGINE',
       'EVIDENCE_ENGINE',
       'federated/local reputation with provenance, freshness and confidence')}


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
