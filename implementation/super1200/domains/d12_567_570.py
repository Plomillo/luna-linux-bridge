#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 567-570. No certification."""
from __future__ import annotations

SPECS = {567: ('API_BACKWARD_COMPATIBILITY', 'GATE', 'old consumer fixtures against new provider'),
 568: ('PROTOCOL_STATE_MACHINE',
       'STATE_MACHINE',
       'states/events/timeouts/retries/forbidden transitions'),
 569: ('PROTOCOL_FORMAL_VERIFICATION',
       'FORMAL_VALIDATION',
       'safety/liveness obligations derived from protocol state machine'),
 570: ('CAPABILITY_NEGOTIATION',
       'PROTOCOL_ENGINE',
       'version/features/constraints negotiation without silent downgrade')}


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
