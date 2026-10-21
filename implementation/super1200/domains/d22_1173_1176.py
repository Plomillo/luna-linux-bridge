#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1173-1176. No certification."""
from __future__ import annotations

SPECS = {1173: ('INCENTIVE_STRUCTURE_ANALYZER',
        'INTERDISCIPLINARY_ANALYZER',
        'modelar beneficios, costes, riesgo percibido, barreras y recompensas como hipótesis '
        'explicativas; no convertir incentivos genéricos en atribución individual'),
 1174: ('OPPORTUNITY_STRUCTURE_ANALYZER',
        'DEFENSIVE_RISK_ANALYZER',
        'relacionar exposición, vulnerabilidad, controles, acceso y oportunidad técnica; '
        'oportunidad ≠ intención y debe mantenerse separada de motivación'),
 1175: ('TARGET_SELECTION_ANALYZER',
        'DEFENSIVE_ANALYSIS_ENGINE',
        'analizar patrones observados de selección de objetivos por sector, tecnología, exposición '
        'o valor operacional; no predecir víctimas específicas sin evidencia suficiente'),
 1176: ('SOCIAL_ENGINEERING_KB',
        'DEFENSIVE_KNOWLEDGE_BASE',
        'patrones de engaño, pretexting, phishing, impersonation y trust exploitation descritos '
        'para detección, educación y prevención; no convertir el KB en generador ofensivo de '
        'campañas')}


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
