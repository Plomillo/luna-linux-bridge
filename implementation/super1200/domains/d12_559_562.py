#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 559-562. No certification."""
from __future__ import annotations

SPECS = {559: ('OPENAPI_REGISTRY',
       'API_REGISTRY',
       'spec ID/version/service/compatibility/security and generated validation'),
 560: ('ASYNCAPI_REGISTRY',
       'API_REGISTRY',
       'event/channel/schema/version and producer/consumer contracts'),
 561: ('PROTOBUF_REGISTRY', 'SCHEMA_REGISTRY', 'field/tag reservation, version and compatibility'),
 562: ('GRPC_PROVIDER',
       'EXT_PROTOCOL_LIBRARY',
       'library/protobuf/TLS/deadline/retry configuration')}


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
