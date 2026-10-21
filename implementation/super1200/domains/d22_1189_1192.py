#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1189-1192. No certification."""
from __future__ import annotations

SPECS = {1189: ('PREVENTION_SIMULATION_ENGINE',
        'DEFENSIVE_SIMULATION_ENGINE',
        'simular controles sobre modelos/fixtures seguros antes de producción; medir eficacia, '
        'impacto operacional, bypass classes y rollback'),
 1190: ('PREVENTIVE_SECURITY_POLICY_SYNTHESIS',
        'SECURITY_POLICY_ENGINE',
        'evidencia+hipótesis+simulación→policy candidate; policy pasa por 101–108, pruebas, '
        'G23/G24 cuando aplique y autorización separada'),
 1191: ('ATTACK_SURFACE_MOTIVATION_LINKER',
        'DEFENSIVE_RISK_GRAPH',
        'relacionar exposición técnica con incentivos/objetivos documentados para priorización '
        'defensiva; motivación nunca sustituye análisis técnico de vulnerabilidad'),
 1192: ('PREDICTIVE_THREAT_HYPOTHESIS',
        'DEFENSIVE_PREDICTIVE_ENGINE',
        'historia+ecosistema+exposición+motivaciones→hipótesis de clases plausibles de amenaza; '
        'cada output incluye premises, supporting evidence, counterevidence, confidence, expiry y '
        'falsification criteria')}


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
