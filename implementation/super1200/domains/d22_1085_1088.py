#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1085-1088. No certification."""
from __future__ import annotations

SPECS = {1085: ('MINIMUM_EVIDENCE_RETENTION',
        'POLICY',
        'retain minimal defensible forensic evidence after sample disposal'),
 1086: ('SAFE_EVIDENCE_DISTILLATION',
        'FORENSIC_ENGINE',
        'live sample→hashes/metadata/behaviors/IOCs/rules/non-executable evidence'),
 1087: ('MALWARE_KNOWLEDGE_EXTRACTION',
        'KNOWLEDGE_ENGINE',
        'extract defensive behaviors/IOCs/lineage/root cause from validated analysis'),
 1088: ('THREAT_BEHAVIOR_SUMMARY',
        'KNOWLEDGE_ARTIFACT',
        'non-executable normalized behavior with evidence links')}


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
