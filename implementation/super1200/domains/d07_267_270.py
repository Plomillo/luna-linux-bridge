#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 267-270. No certification."""
from __future__ import annotations

SPECS = {267: ('JULIA_PROVIDER',
       'PROGRAMMING_LANGUAGE_RUNTIME',
       'runtime/project/manifest/artifact identities'),
 268: ('DUCKDB_PROVIDER',
       'EXT_LIBRARY_DATABASE',
       'library/DB format/version, read/write isolation and deterministic queries'),
 269: ('APACHE_ARROW_PROVIDER', 'EXT_LIBRARY_STANDARD', 'schema/version/endian/type compatibility'),
 270: ('POLARS_PROVIDER', 'EXT_LIBRARY', 'package version, lazy plan and deterministic transforms')}


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
