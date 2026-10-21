#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1197-1200. No certification."""
from __future__ import annotations

SPECS = {1197: ('HUMAN_THREAT_KNOWLEDGE_PROVENANCE',
        'PROVENANCE_ENGINE',
        'cada afirmación sobre motivación, conducta humana, criminología, filosofía, teología, '
        'sociología o economía conserva fuente, disciplina, contexto, población, época, método, '
        'uncertainty y transformations; inferencias interdisciplinarias nunca borran procedencia '
        'disciplinaria'),
 1198: ('INTERDISCIPLINARY_THREAT_SYNTHESIS',
        'DEFENSIVE_SYNTHESIS_ENGINE',
        'integrar ciberseguridad, historia, criminología, sociología, economía, psicología moral, '
        'antropología, filosofía y teología sólo después de análisis disciplinares separados; '
        'conflictos preservados; technical finding, human interpretation y normative judgment '
        'permanecen tipos distintos'),
 1199: ('EVIL_TO_CYBER_HERMENEUTIC_BOUNDARY',
        'EPISTEMIC_GOVERNANCE_BOUNDARY',
        'separar estrictamente PHILOSOPHICAL_THEOLOGICAL_INTERPRETATION de '
        'TECHNICAL_SECURITY_DETERMINATION; conceptos de mal, pecado, moralidad, cultura, religión '
        'o antropología jamás constituyen firmas técnicas ni evidencia suficiente de malware, '
        'intrusión o intención criminal; sólo evidencia técnica/empírica aplicable puede producir '
        'hallazgos técnicos'),
 1200: ('PREINFECTION_PREVENTION_GATE',
        'GLOBAL_PREINFECTION_SECURITY_GATE',
        'último control preventivo antes de '
        'DOWNLOAD/IMPORT/EXECUTE/INSTALL/LOAD/CONNECT/GRANT_PRIVILEGE; consulta identidad, '
        'provenance, provider, supply-chain, vulnerabilities, reputation, scanning, requested '
        'capabilities, network/filesystem/resource envelope, authorization, uncertainty y '
        'rollback; resultado sólo ALLOW/DENY/HOLD/SANDBOX según política; ningún scanner, modelo, '
        'reputación, proveedor, filosofía, teología o consenso aislado puede autorizar; G23/G24 y '
        'autorización operacional permanecen separados')}


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
