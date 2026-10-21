#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1045-1048. No certification."""
from __future__ import annotations

SPECS = {1045: ('UTILITY_DEPENDENCY_ANALYZER',
        'ANALYZER',
        'consumers/dependencies/data/protocol expectations'),
 1046: ('QUARANTINE_BLOCKER_DETECTOR',
        'ANALYZER',
        'which missions/capabilities cannot proceed and why'),
 1047: ('BLOCKED_CAPABILITY_ROUTER',
        'ROUTING_ENGINE',
        'find existing certified/authorized alternative before new implementation'),
 1048: ('SAFE_PROVIDER_SEARCH',
        'PROVIDER_DISCOVERY_ENGINE',
        'registry-first then official trusted providers; provenance/license/security comparison')}


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
