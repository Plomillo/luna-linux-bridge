#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1057-1060. No certification."""
from __future__ import annotations

SPECS = {1057: ('SUBSTITUTE_PROVENANCE',
        'PROVENANCE_RECORD',
        'requirements/source/deps/toolchain/build/decisions all traced'),
 1058: ('SUBSTITUTE_SBOM',
        'SBOM_ARTIFACT',
        'complete direct/transitive components with hashes/licenses'),
 1059: ('SUBSTITUTE_REPRODUCIBLE_BUILD',
        'BUILD_ASSURANCE',
        'hermetic rebuild or explicit reproducibility limitations'),
 1060: ('SUBSTITUTE_SECURITY_BASELINE',
        'SECURITY_BASELINE',
        'privilege/network/filesystem/dependency/update requirements stricter than rejected '
        'object')}


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
