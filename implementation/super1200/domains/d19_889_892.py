#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 889-892. No certification."""
from __future__ import annotations

SPECS = {889: ('FILE_REPUTATION_ENGINE',
       'EVIDENCE_ENGINE',
       'reputation is weighted signal with provenance/freshness, never proof'),
 890: ('HASH_REPUTATION_ENGINE',
       'EVIDENCE_ENGINE',
       'algorithm/hash/source/date and collision/context handling'),
 891: ('PACKER_DETECTOR',
       'DETECTOR',
       'packer/obfuscation signal classified as suspicious, not malicious by itself'),
 892: ('SCRIPT_MALWARE_ANALYZER',
       'DEFENSIVE_ANALYZER',
       'static control/data-flow and policy checks; no execution outside sandbox')}


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
