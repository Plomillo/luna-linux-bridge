#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 913-916. No certification."""
from __future__ import annotations

SPECS = {913: ('SBOM_SECURITY_ANALYZER',
       'SECURITY_ANALYZER',
       'SBOM components→vulns/license/provenance with exact versions'),
 914: ('DEPENDENCY_VULNERABILITY_ENGINE',
       'SECURITY_ANALYZER',
       'direct/transitive dependencies, version ranges, reachability and fix paths'),
 915: ('MALICIOUS_DEPENDENCY_DETECTOR',
       'SUPPLY_CHAIN_DETECTOR',
       'provenance/signature/maintainer/name/install-script anomalies; suspicion explicit'),
 916: ('TYPOSQUATTING_DETECTOR',
       'SUPPLY_CHAIN_DETECTOR',
       'name similarity plus provenance/context, no automatic malicious verdict')}


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
