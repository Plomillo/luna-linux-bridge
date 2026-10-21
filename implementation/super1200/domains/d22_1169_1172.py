#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1169-1172. No certification."""
from __future__ import annotations

SPECS = {1169: ('ECONOMICS_OF_CYBERCRIME',
        'INTERDISCIPLINARY_DOMAIN_ENGINE',
        'modelar incentivos, costes, mercados, beneficios esperados y estructuras económicas con '
        'unidades, temporalidad, fuente y márgenes de incertidumbre'),
 1170: ('HISTORY_OF_CYBERCRIME',
        'HISTORICAL_DOMAIN_ENGINE',
        'cronología de técnicas, ecosistemas, incentivos y defensas preservando contexto '
        'histórico, fuentes y cambios semánticos; evitar anacronismo causal'),
 1171: ('THREAT_ACTOR_MOTIVATION_TAXONOMY',
        'DEFENSIVE_ONTOLOGY',
        'clasificar motivaciones documentadas como '
        'FINANCIAL/ESPIONAGE/IDEOLOGICAL/DISRUPTION/REVENGE/EXPERIMENTATION/OTHER/UNKNOWN con '
        'confidence y provenance; motivación atribuida nunca equivale a identidad del actor'),
 1172: ('THREAT_OBJECTIVE_ENGINE',
        'DEFENSIVE_ANALYSIS_ENGINE',
        'inferir objetivos sólo desde conducta/campaña/evidencia observada; distinguir objetivo '
        'confirmado, probable, posible y desconocido')}


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
