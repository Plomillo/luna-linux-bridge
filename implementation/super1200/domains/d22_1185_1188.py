#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1185-1188. No certification."""
from __future__ import annotations

SPECS = {1185: ('ATTRIBUTION_UNCERTAINTY_GATE',
        'EPISTEMIC_SECURITY_GATE',
        'ninguna atribución supera el nivel sustentado por evidencia; considerar deception, shared '
        'tooling, false flags, copied infrastructure y source dependence; UNKNOWN/CONFLICT '
        'permanecen bloqueantes para acciones basadas en identidad'),
 1186: ('HUMAN_INTENT_TECHNICAL_MAPPING',
        'DEFENSIVE_SEMANTIC_ADAPTER',
        'mapear objetivos/intenciones hipotéticas a señales técnicas observables únicamente '
        'mediante relaciones documentadas; prohibido invertir automáticamente señal '
        'técnica→certeza sobre intención humana'),
 1187: ('PRE_ATTACK_INDICATOR_ENGINE',
        'DEFENSIVE_DETECTION_ENGINE',
        'detectar precursores como targeting documentado, anomalías de acceso, cambios de '
        'exposición o infraestructura sospechosa mediante múltiples señales; evitar false-positive '
        'escalation automática'),
 1188: ('PREVENTION_HYPOTHESIS_ENGINE',
        'DEFENSIVE_REASONING_ENGINE',
        'para cada amenaza plausible formular control preventivo, mecanismo causal esperado, '
        'evidencia requerida y posibles efectos secundarios')}


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
