#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1149-1152. No certification."""
from __future__ import annotations

SPECS = {1149: ('DEFENSIVE_RULE_COMPILER',
        'RULE_COMPILER',
        'validated knowledge→candidate YARA/SIEM/etc rule plus tests, never auto-certify'),
 1150: ('PREVENTIVE_CONTROL_SYNTHESIS',
        'PREVENTION_ENGINE',
        'behavior classes→least-disruptive preventive controls with simulation'),
 1151: ('THREAT_KNOWLEDGE_DEDUPLICATION',
        'DATA_ENGINE',
        'semantic/content duplicate detection preserving source references'),
 1152: ('THREAT_KNOWLEDGE_COMPRESSION',
        'DATA_ENGINE',
        'compact representation without semantic/provenance loss')}


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
