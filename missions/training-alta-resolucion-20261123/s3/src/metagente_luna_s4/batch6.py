"""Cases resolved from the operation text, not from the identifier."""
from __future__ import annotations

from metagente_luna_s4.runner import execute
from metagente_luna_s4.semantic import interpret

OPERATIONS = [
    ("MGL5-INF-0105", "Ordenar registros por edad conservando la estabilidad entre edades iguales."),
    ("MGL5-INF-0106", "Ordenar 10.000 enteros en orden descendente."),
    ("MGL5-INF-0109", "Ejecutar push, pop y peek con una secuencia que también provoca underflow."),
    ("MGL5-INF-0114", "Buscar ruta en grafo de seis nodos conocido."),
    ("MGL5-INF-0609", "Multiplicar matrices 2×3 y 3×2 conocidas."),
    ("MGL5-INF-0611", "Calcular determinante de matriz 3×3 de referencia."),
    ("MGL5-INF-0632", "Calcular media móvil de ventana 3 sobre una serie con semilla declarada."),
]


def run_all() -> list[dict]:
    rows = []
    for case_id, operation in OPERATIONS:
        plan = interpret(operation)
        if plan["plan_status"] != "VALIDATED":
            rows.append({
                "case_id": case_id,
                "operation": operation,
                "plan_status": plan["plan_status"],
                "missing_information": plan["missing_information"],
                "execution_status": plan["plan_status"],
                "observed": None,
                "backend": "LOCAL_TEST_ONLY",
                "c05_gate": "NOT_PASSED",
            })
            continue
        runs = [execute(plan["capability"], plan["arguments"], case_id) for _ in range(3)]
        observed = [run["observed"] for run in runs]
        stable = all(item == observed[0] for item in observed)
        ok = all(run["execution_status"] == "EXECUTED" for run in runs) and stable
        rows.append({
            "case_id": case_id,
            "operation": operation,
            "capability": plan["capability"],
            "observed": observed[0],
            "execution_status": "CRITERION_MET" if ok else runs[0]["execution_status"],
            "repetitions": [run["run_id"] for run in runs],
            "backend": "LOCAL_TEST_ONLY",
            "c05_gate": "NOT_PASSED",
        })
    return rows
