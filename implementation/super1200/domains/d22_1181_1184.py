#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1181-1184. No certification."""
from __future__ import annotations

SPECS = {1181: ('CYBERCRIME_ECOSYSTEM_MODEL',
        'DEFENSIVE_ECOSYSTEM_GRAPH',
        'modelar roles, infraestructura, servicios, monetización, relaciones y dependencias a '
        'nivel abstracto/defensivo; separar observación, inferencia y atribución'),
 1182: ('DARK_WEB_DEFENSIVE_INTELLIGENCE_INTERFACE',
        'DEFENSIVE_INTELLIGENCE_INTERFACE',
        'interfaz de sólo inteligencia defensiva agregada; legal_basis, provider_id, '
        'collection_method, timestamp, provenance, data-minimization y prohibited_actions '
        'obligatorios; sin adquisición de credenciales, malware, bienes ilícitos ni interacción '
        'encubierta no autorizada'),
 1183: ('ILLICIT_MARKET_SIGNAL_ANALYZER',
        'DEFENSIVE_ANALYTICS_ENGINE',
        'analizar únicamente señales agregadas sobre disponibilidad, precios, demanda o cambios de '
        'ecosistema; ninguna transacción, intermediación o adquisición de material ilícito'),
 1184: ('CAMPAIGN_INTENT_ANALYZER',
        'DEFENSIVE_ANALYSIS_ENGINE',
        'objetivos/tácticas/selección observada→hipótesis de intención con confidence y '
        'alternatives; evitar atribución categórica sin evidencia')}


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
