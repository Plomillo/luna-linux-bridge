#!/usr/bin/env python3
"""D10 reviewed name-specific material for capabilities 450-453. No certification."""
from __future__ import annotations

SPECS = {450: ('BYTECODE_VM_FACTORY',
       'FACTORY',
       'bytecode spec, verifier, sandbox/resource limits and compatibility'),
 451: ('INTERPRETER_FACTORY',
       'FACTORY',
       'semantics-conformant interpreter, resource bounds and errors'),
 452: ('COMPILER_FACTORY', 'FACTORY', 'front-end→IR→codegen→link→conformance/reproducibility'),
 453: ('JIT_PROVIDER',
       'PROVIDER_INTERFACE',
       'executable-memory security, target identity and cache invalidation')}


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
