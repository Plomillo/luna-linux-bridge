#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 409-412. No certification."""
from __future__ import annotations

SPECS = {409: ('YOCTO_PROVIDER',
       'EXT_OS_BUILD_TOOLCHAIN',
       'layer revisions, bitbake config and source mirrors'),
 410: ('DEBIAN_IMAGE_PROVIDER',
       'EXT_OS_DISTRIBUTION_PROVIDER',
       'release/repo snapshot/signatures/packages/image hash'),
 411: ('PACKAGE_REPOSITORY_FACTORY',
       'FACTORY',
       'package identities, metadata indexes, signing and immutable snapshots'),
 412: ('PACKAGE_SIGNING',
       'SIGNING_ENGINE',
       'offline/controlled key custody, package+metadata verification')}


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
