#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 869-872. No certification."""
from __future__ import annotations

SPECS = {869: ('SECURITY_EVIDENCE_LEDGER',
       'LEDGER',
       'raw finding/evidence/tool/version/time/host/object/chain-of-custody'),
 870: ('SECURITY_FINDING_IDENTITY',
       'IDENTITY_PRIMITIVE',
       'stable finding ID separate from indicator/object identity'),
 871: ('SECURITY_CONFIDENCE_ENGINE',
       'EPISTEMIC_ENGINE',
       'confidence calibrated by detector/domain/history; suspicion≠malware'),
 872: ('SECURITY_UNCERTAINTY_ADAPTER',
       'ADAPTER',
       'map security unknowns into 641–660 without losing incident context')}


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
