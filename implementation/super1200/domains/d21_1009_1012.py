#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1009-1012. No certification."""
from __future__ import annotations

SPECS = {1009: ('CONTENT_DISARM_RECONSTRUCTION',
        'SANITIZATION_ENGINE',
        'remove unnecessary active functionality and rebuild passive representation'),
 1010: ('FORMAT_AWARE_SANITIZER',
        'SANITIZATION_ORCHESTRATOR',
        'dispatch by verified format to specialized sanitizer; no byte-pattern-only generic '
        'cleaning'),
 1011: ('PDF_SANITIZER',
        'FORMAT_ENGINE',
        'JS/actions/attachments/embedded files/forms/structure handled explicitly'),
 1012: ('OFFICE_DOCUMENT_SANITIZER',
        'FORMAT_ENGINE',
        'OOXML parts/macros/embeddings/external links while preserving document semantics')}


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
