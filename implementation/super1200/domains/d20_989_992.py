#!/usr/bin/env python3
"""D20 reviewed name-specific material for capabilities 989-992. No certification."""
from __future__ import annotations

SPECS = {989: ('INITIAL_ACCESS_ANALYZER',
       'FORENSIC_ANALYZER',
       'map observed evidence to plausible initial-access class, not offensive reproduction'),
 990: ('ROOT_CAUSE_SECURITY_ANALYZER',
       'INCIDENT_ANALYZER',
       'separate malicious artifact, exploited weakness, config/process cause and enabling '
       'conditions'),
 991: ('MALWARE_ERADICATION_ENGINE',
       'REMEDIATION_ENGINE',
       'only confirmed artifacts, explicit authorization, checkpoint, exact targets and '
       'verification'),
 992: ('PERSISTENCE_ERADICATION_ENGINE',
       'REMEDIATION_ENGINE',
       'remove only evidenced persistence mechanisms and verify expected services remain')}


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
