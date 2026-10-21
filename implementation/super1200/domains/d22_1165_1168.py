#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1165-1168. No certification."""
from __future__ import annotations

SPECS = {1165: ('ANTHROPOLOGY_OF_HARM_ENGINE',
        'INTERPRETIVE_DOMAIN_ENGINE',
        'analizar manifestaciones humanas y culturales del daño mediante contexto histórico/social '
        'verificable; prohibido convertir etnia, religión, nacionalidad u otra característica '
        'protegida en indicador de riesgo técnico'),
 1166: ('MORAL_PSYCHOLOGY_ADAPTER',
        'DISCIPLINE_ADAPTER',
        'integrar constructos de psicología moral sólo con definición operacional, fuente, '
        'población, limitaciones y nivel de evidencia; no diagnosticar individuos ni inferir '
        'intención maliciosa desde perfiles psicológicos'),
 1167: ('CRIMINOLOGY_ADAPTER',
        'DISCIPLINE_ADAPTER',
        'integrar teorías criminológicas como modelos explicativos con alcance, población, '
        'contexto y limitaciones; jamás tratar correlaciones criminológicas como prueba individual '
        'de culpabilidad o amenaza'),
 1168: ('SOCIOLOGY_OF_CYBERCRIME',
        'INTERDISCIPLINARY_DOMAIN_ENGINE',
        'modelar redes, roles, instituciones, normas y dinámicas sociales del cybercrime a nivel '
        'agregado; distinguir observación, teoría y atribución; no perfilar grupos protegidos')}


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
