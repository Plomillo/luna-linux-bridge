#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 539-542. No certification."""
from __future__ import annotations

SPECS = {539: ('CORRUPTION_SIMULATOR', 'SIMULATOR', 'copy-only corruption cases; originals immutable'),
 540: ('CERTIFICATE_EXPIRY_SIMULATOR',
       'SIMULATOR',
       'simulate trust/certificate expiry without altering production clocks'),
 541: ('REBOOT_SIMULATOR',
       'SIMULATOR/TEST',
       'VM/emulator first; physical reboot requires explicit authorization'),
 542: ('POWER_LOSS_SIMULATOR', 'SIMULATOR', 'abrupt-stop tests only in disposable targets')}


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
