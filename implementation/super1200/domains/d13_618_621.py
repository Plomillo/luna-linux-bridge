#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 618-621. No certification."""
from __future__ import annotations

SPECS = {618: ('EXECUTABLE_EXAMPLE_ENGINE',
       'TESTABLE_CONTENT_ENGINE',
       'examples execute in CI/sandbox and bind outputs'),
 619: ('DOCUMENTATION_CI', 'CI_FABRIC', 'links/examples/schema/generated docs tested per commit'),
 620: ('DOC_CODE_SYNCHRONIZATION',
       'DOCUMENTATION_ENGINE',
       'derive shared facts from code/manifests rather than duplicate'),
 621: ('DOCUMENTATION_DRIFT_DETECTOR',
       'VALIDATION_ENGINE',
       'detect API/config/example/doc divergence')}


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
