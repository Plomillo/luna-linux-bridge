#!/usr/bin/env python3
"""D10 reviewed name-specific material for capabilities 458-461. No certification."""
from __future__ import annotations

SPECS = {458: ('LANGUAGE_TEST_SUITE',
       'TEST_SUITE',
       'lexer/parser/types/semantics/runtime/package compatibility and negative tests'),
 459: ('SEMANTICS_SPEC',
       'NORMATIVE_SPEC',
       'versioned normative semantics separate from implementation'),
 460: ('FORMAL_SEMANTICS_PROVIDER',
       'FORMAL_PROVIDER',
       'executable/provable semantics linked to 459'),
 461: ('ENGINE_FACTORY',
       'FACTORY',
       'engine template with identity/interface/deps/tests/provenance/security/rollback')}


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
