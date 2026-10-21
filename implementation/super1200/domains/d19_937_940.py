#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 937-940. No certification."""
from __future__ import annotations

SPECS = {937: ('WORKFLOW_SECURITY_ANALYZER',
       'SECURITY_ANALYZER',
       'permissions/triggers/untrusted input/secrets/pinning/runner exposure'),
 938: ('BRANCH_PROTECTION_AUDITOR',
       'AUDITOR',
       'read effective protection/rules/status checks; UNKNOWN when permissions unavailable'),
 939: ('REPOSITORY_TAMPER_DETECTOR',
       'DETECTOR',
       'protected refs/files/history changes against expected authority and baseline'),
 940: ('CANONICAL_ARTIFACT_SECURITY_GUARD',
       'SECURITY_GATE',
       'Louksna/frozen artifacts exact hash/authorized mutation only; fail closed on drift')}


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
