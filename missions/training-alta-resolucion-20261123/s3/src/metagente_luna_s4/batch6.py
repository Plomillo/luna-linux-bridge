"""Literal training instructions. The identifier is recorded after interpretation, never used to choose the operation."""
from __future__ import annotations

import json
import random
from pathlib import Path

from metagente_luna_s3.interpret import interpret
from metagente_luna_s4.runner import execute

OPERATIONS = [
    ("MGL5-INF-0105", "Ordenar registros por edad conservando orden entre edades iguales."),
    ("MGL5-INF-0106", "Ordenar 10.000 enteros en orden descendente."),
    ("MGL5-INF-0109", "Ejecutar push, pop y peek con secuencia predefinida."),
    ("MGL5-INF-0114", "Buscar ruta en grafo de seis nodos conocido."),
    ("MGL5-INF-0609", "Multiplicar matrices 2×3 y 3×2 conocidas."),
    ("MGL5-INF-0611", "Calcular determinante de matriz 3×3 de referencia."),
    ("MGL5-INF-0632", "Calcular media móvil de ventana 3 sobre fixture."),
]

_FIXTURE = json.loads(
    (Path(__file__).resolve().parents[2] / "fixtures" / "derived_parameters.json").read_text(encoding="utf-8")
)

# The source fixes a 10,000-integer fixture and seed 0106 but no literal values.
# Use the minimal integer domain 0..9999 and a seeded shuffle; no runtime entropy.
_DESCENDING_VALUES = list(range(10_000))
random.Random(106).shuffle(_DESCENDING_VALUES)

# Only candidates whose source-derived fixture and registered capability are
# complete are exposed to the C05 plan compiler. Other interpreter candidates
# remain visible in the coverage matrix as blocked/ambiguous.
CASES = [
    {
        "case_id": "MGL5-INF-0106",
        "capability_id": "descending_values",
        "arguments": {"values": _DESCENDING_VALUES},
        "fixture_provenance": "SOURCE_SEED_0106; range(10000); random.Random(106).shuffle",
    },
    {
        "case_id": "MGL5-INF-0105",
        "capability_id": "stable_ages",
        "arguments": {"records": _FIXTURE["stable-ages"]["records"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#stable-ages",
    },
    {
        "case_id": "MGL5-INF-0109",
        "capability_id": "stack_sequence",
        "arguments": {"steps": _FIXTURE["stack-script"]["steps"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#stack-script",
    },
]


def run_all() -> list[dict]:
    rows = []
    for case_id, operation in OPERATIONS:
        plan = interpret(operation)
        if plan.status != "READY":
            rows.append({
                "case_id": case_id,
                "operation": operation,
                "plan_status": plan.status,
                "missing_information": plan.missing,
                "execution_status": "BLOCKED" if plan.status == "BLOCKED" else plan.status,
                "observed": None,
                "backend": "LOCAL_TEST_ONLY",
                "c05_gate": "NOT_PASSED",
            })
            continue
        arguments = {item.name: item.value for item in plan.arguments}
        runs = [execute(plan.intent, arguments, case_id) for _ in range(3)]
        observed = [run["observed"] for run in runs]
        stable = all(item == observed[0] for item in observed)
        ok = all(run["execution_status"] == "EXECUTED" for run in runs) and stable
        rows.append({
            "case_id": case_id,
            "operation": operation,
            "capability": plan.intent,
            "observed": observed[0],
            "execution_status": "CRITERION_MET" if ok else runs[0]["execution_status"],
            "repetitions": [run["run_id"] for run in runs],
            "backend": "LOCAL_TEST_ONLY",
            "c05_gate": "NOT_PASSED",
        })
    return rows
