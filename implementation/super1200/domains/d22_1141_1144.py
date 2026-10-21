#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1141-1144. No certification."""
from __future__ import annotations

SPECS = {1141: ('EXPLOITED_VULNERABILITY_LINKER',
        'GRAPH_ENGINE',
        'malware/campaign↔CVE links only with source/confidence'),
 1142: ('PLATFORM_TARGET_GRAPH',
        'GRAPH',
        'family/behavior↔platform/version relations with evidence'),
 1143: ('MALWARE_TECHNOLOGY_EVOLUTION',
        'ANALYSIS_ENGINE',
        'time-series of behavior/technology changes, descriptive not predictive alone'),
 1144: ('THREAT_SIMILARITY_ENGINE',
        'ANALYSIS_ENGINE',
        'feature/behavior similarity with explainable evidence and uncertainty')}


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
