#!/usr/bin/env python3
"""D10 reviewed name-specific material for capabilities 438-441. No certification."""
from __future__ import annotations

SPECS = {438: ('LANGUAGE_FACTORY', 'FACTORY', 'grammar→AST→types→IR→runtime/tooling/tests/package manager'),
 439: ('GRAMMAR_FACTORY', 'FACTORY', 'versioned grammar and ambiguity/conformance tests'),
 440: ('LEXER_GENERATOR',
       'LANGUAGE_TOOL',
       'token spec, Unicode/error behavior and generated artifact hash'),
 441: ('PARSER_GENERATOR',
       'LANGUAGE_TOOL',
       'grammar version, parser determinism/error recovery and tests')}


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
