#!/usr/bin/env python3
"""D10 reviewed name-specific material for capabilities 446-449. No certification."""
from __future__ import annotations

SPECS = {446: ('IR_FACTORY', 'FACTORY', 'typed/versioned IR with verified lowering contracts'),
 447: ('LLVM_PROVIDER', 'EXT_COMPILER_INFRASTRUCTURE', 'version/target/features/build provenance'),
 448: ('MLIR_PROVIDER', 'EXT_COMPILER_INFRASTRUCTURE', 'dialect/pass/version compatibility'),
 449: ('CODEGEN_ENGINE',
       'COMPILER_ENGINE',
       'IR→target mapping, deterministic flags and differential tests')}


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
