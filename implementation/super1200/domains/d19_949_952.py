#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 949-952. No certification."""
from __future__ import annotations

SPECS = {949: ('LUNA_DEFENDER_CAPABILITY_BASELINE',
       'BASELINE',
       'expected files/network/privileges/providers/resources per capability'),
 950: ('LUNA_DEFENDER_CUSTOM_RULE_FACTORY',
       'FACTORY',
       'evidence→candidate rule→corpus tests→independent review; never auto-activate'),
 951: ('LUNA_DEFENDER_RULE_TEST_LAB',
       'LAB',
       'benign/malicious/synthetic corpora, resource tests and exact rule version'),
 952: ('LUNA_DEFENDER_FALSE_POSITIVE_GATE',
       'GATE',
       'false-positive threshold by domain plus reversible quarantine preference')}


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
