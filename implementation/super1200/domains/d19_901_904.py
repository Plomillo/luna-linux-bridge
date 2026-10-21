#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 901-904. No certification."""
from __future__ import annotations

SPECS = {901: ('VULNERABILITY_MANAGEMENT_FABRIC',
       'SECURITY_FABRIC',
       'component→vuln→applicability→reachability→exploitability→priority→patch→verification'),
 902: ('OSV_PROVIDER',
       'DATA_FEED_API_PROVIDER',
       'query/snapshot version/time/source and package ecosystem normalization'),
 903: ('NVD_ADAPTER',
       'DATA_FEED_ADAPTER',
       'feed/version/date/CVE/CPE mappings and rate/cache policy'),
 904: ('CVE_IDENTITY_REGISTRY', 'REGISTRY', 'CVE aliases/source/status/affected-version ranges')}


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
