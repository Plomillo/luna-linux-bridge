#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1097-1100. No certification."""
from __future__ import annotations

SPECS = {1097: ('SANDBOX_INTEGRITY_MONITOR',
        'MONITOR',
        'sandbox config/hypervisor/containers/host boundary health'),
 1098: ('ANALYZER_COMPROMISE_MONITOR',
        'MONITOR',
        'parser/scanner crash/exploit/anomaly and dependency advisory monitoring'),
 1099: ('SECURITY_TOOL_ISOLATION',
        'SECURITY_BOUNDARY',
        'security parsers/scanners run least-privileged with constrained input/output/network'),
 1100: ('DISPOSABLE_ANALYSIS_ENVIRONMENT',
        'SANDBOX_PATTERN',
        'recreate from trusted image, destroy state after run, preserve only evidence')}


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
