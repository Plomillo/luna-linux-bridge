#!/usr/bin/env python3
"""D20 reviewed name-specific material for capabilities 969-972. No certification."""
from __future__ import annotations

SPECS = {969: ('QUARANTINE_CHAIN_OF_CUSTODY',
       'AUDIT_LEDGER',
       'detect/move/access/analyze/decide actor/time/action sequence'),
 970: ('QUARANTINE_EXPIRATION_POLICY',
       'POLICY',
       'retention by risk/research/evidence need, never indefinite by default'),
 971: ('SAFE_SAMPLE_REPRESENTATION',
       'SECURITY_ARTIFACT',
       'prefer hashes/IOCs/rules/behavior summaries over live samples where sufficient'),
 972: ('FORENSIC_ANALYSIS_FABRIC',
       'DEFENSIVE_FORENSIC_FABRIC',
       'triage→sandbox→recorders→timeline→graph→IOCs→classification')}


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
