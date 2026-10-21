#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1161-1164. No certification."""
from __future__ import annotations

SPECS = {1161: ('HUMAN_ORIGIN_THREAT_FABRIC',
        'INTERDISCIPLINARY_DEFENSIVE_FABRIC',
        'technical-human context without protected-trait profiling or security verdicts from '
        'humanities claims'),
 1162: ('HUMAN_HARM_ONTOLOGY', 'ONTOLOGY', 'harm/intention/context'),
 1163: ('PHILOSOPHY_OF_EVIL_ENGINE',
        'INTERPRETIVE_DOMAIN_ENGINE',
        'analizar concepciones filosóficas del mal distinguiendo autor, tradición, época, texto, '
        'interpretación e inferencia; ninguna tesis filosófica produce indicador técnico de '
        'amenaza por sí misma'),
 1164: ('THEOLOGY_OF_EVIL_ENGINE',
        'THEOLOGICAL_DOMAIN_ENGINE',
        'aplicar configuración teológica canónica de Louksna donde corresponda; separar texto, '
        'exégesis, interpretación, síntesis doctrinal y aplicación; controles contra eiségesis, '
        'proof-texting, anacronismo, falacia lexical y sobrecarga semántica; ninguna afirmación '
        'teológica sustituye evidencia técnica de seguridad')}


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
