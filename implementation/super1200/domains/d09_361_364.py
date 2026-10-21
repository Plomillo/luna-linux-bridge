#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 361-364. No certification."""
from __future__ import annotations

SPECS = {361: ('REMOTE_DATASET_INSPECTOR',
       'DATA_ENGINE',
       'metadata/schema/sample/range only; no full fetch by default'),
 362: ('HTTP_RANGE_READER',
       'NETWORK_LIBRARY',
       'TLS, redirect policy, range/ETag validation, size caps'),
 363: ('S3_RANGE_PROVIDER',
       'EXT_SERVICE_ADAPTER',
       'credential scope, bucket/object/version identity and ranged hashes'),
 364: ('PARQUET_PUSHDOWN', 'DATA_ENGINE', 'projection/filter semantics and schema version')}


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
