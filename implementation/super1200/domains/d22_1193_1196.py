#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1193-1196. No certification."""
from __future__ import annotations

SPECS = {1193: ('THREAT_EARLY_WARNING_ENGINE',
        'DEFENSIVE_WARNING_ENGINE',
        'combinar 1187/1192 con vulnerabilidad, exposición y baseline; warning≠incident; '
        'severity/confidence/time horizon/actionability diferenciados'),
 1194: ('PREVENT_BEFORE_DOWNLOAD_ENGINE',
        'PRE_EXECUTION_SECURITY_GATE',
        'antes de adquirir objeto verificar necesidad, source, identity, reputation, provenance, '
        'signatures/hashes, expected content, risk y safe acquisition path; UNKNOWN '
        'crítico→DENY/HOLD; nunca descargar primero para decidir después cuando la información '
        'preventiva sea suficiente'),
 1195: ('PREVENT_BEFORE_EXECUTION_ENGINE',
        'PRE_EXECUTION_SECURITY_GATE',
        'antes de ejecutar verificar artifact identity, provenance, scan status, sandbox '
        'requirement, signer, dependencies, requested privileges, network/filesystem envelope y '
        'applicable authorization; suspicious/inconclusive→sandbox/HOLD'),
 1196: ('PREVENT_BEFORE_PRIVILEGE_ENGINE',
        'PRIVILEGE_SECURITY_GATE',
        'antes de elevar privilegios exigir exact actor/action/object/scope/time/lease, least '
        'privilege, single-use/revocation where applicable, binary/artifact identity, risk, '
        'rollback and audit readiness; UNKNOWN/CONFLICT→DENY')}


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
