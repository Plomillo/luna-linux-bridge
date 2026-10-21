#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1001-1004. No certification."""
from __future__ import annotations

SPECS = {1001: ('ARTIFACT_SANITIZATION_FABRIC',
        'SANITIZATION_FABRIC',
        'decompose→localize→feasibility→minimal transform→reconstruct→verify→new identity'),
 1002: ('ARTIFACT_COMPONENT_GRAPH',
        'GRAPH',
        'container→components→active relationships→content identities'),
 1003: ('ACTIVE_CONTENT_DETECTOR',
        'DETECTOR',
        'macros/scripts/embedded executables/actions/links classified with evidence'),
 1004: ('MALICIOUS_COMPONENT_LOCALIZER',
        'ANALYZER',
        'map finding to exact component/behavior; inconclusive remains inconclusive')}


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
