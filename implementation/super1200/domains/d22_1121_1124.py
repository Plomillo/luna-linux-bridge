#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1121-1124. No certification."""
from __future__ import annotations

SPECS = {1121: ('HISTORICAL_THREAT_INTELLIGENCE_FABRIC',
        'DEFENSIVE_KNOWLEDGE_FABRIC',
        'history/taxonomy/families/behaviors/TTPs/IOCs/vulns/provenance/confidence'),
 1122: ('MALWARE_HISTORY_REGISTRY',
        'KNOWLEDGE_REGISTRY',
        'family/campaign/event chronology with source confidence'),
 1123: ('MALWARE_TAXONOMY_ENGINE',
        'ONTOLOGY_ENGINE',
        'behavior/function categories versioned; labels not proof'),
 1124: ('MALWARE_FAMILY_REGISTRY',
        'KNOWLEDGE_REGISTRY',
        'family aliases/behavior/source/confidence')}


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
