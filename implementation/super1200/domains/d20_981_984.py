#!/usr/bin/env python3
"""D20 reviewed name-specific material for capabilities 981-984. No certification."""
from __future__ import annotations

SPECS = {981: ('BEHAVIOR_GRAPH', 'FORENSIC_GRAPH', 'process/file/network/persistence causal relations'),
 982: ('IOC_EXTRACTION_ENGINE',
       'DEFENSIVE_ENGINE',
       'derive IOCs with source event/provenance/confidence/expiry'),
 983: ('MALWARE_CLASSIFICATION_GATE',
       'SECURITY_GATE',
       'BENIGN/SUSPICIOUS/MALICIOUS/INCONCLUSIVE; evidence thresholds predeclared'),
 984: ('BENIGN_RELEASE_GATE',
       'SECURITY_GATE',
       'integrity/source/analysis/residual risk verified before release')}


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
