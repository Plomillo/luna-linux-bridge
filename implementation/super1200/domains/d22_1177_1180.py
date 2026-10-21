#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1177-1180. No certification."""
from __future__ import annotations

SPECS = {1177: ('DECEPTION_PATTERN_REGISTRY',
        'DEFENSIVE_REGISTRY',
        'pattern_id, medio, señales, objetivo, contexto, source, confidence, false-positive '
        'profile y controles preventivos'),
 1178: ('TRUST_ABUSE_ANALYZER',
        'DEFENSIVE_ANALYZER',
        'detectar abuso de relaciones de confianza, identidad, proveedores, privilegios o procesos '
        'desde señales observables; confianza social no se equipara automáticamente con riesgo'),
 1179: ('HUMAN_VULNERABILITY_MODEL',
        'DEFENSIVE_HUMAN_FACTORS_MODEL',
        'modelar factores situacionales y de proceso —fatiga operacional, presión, ambigüedad, '
        'exceso de privilegios, interfaces engañosas— evitando diagnósticos personales, atributos '
        'sensibles o profiling discriminatorio'),
 1180: ('SECURITY_DECISION_BIAS_ANALYZER',
        'METACOGNITIVE_SECURITY_ENGINE',
        'detectar anchoring, confirmation bias, automation bias, normalcy bias, sunk cost y '
        'premature closure en decisiones documentadas; salida=alerta/revisión, nunca sustitución '
        'de autoridad')}


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
