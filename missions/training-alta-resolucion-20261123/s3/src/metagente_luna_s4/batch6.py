"""Literal training instructions. The identifier is recorded after interpretation, never used to choose the operation."""
from __future__ import annotations

import json
from pathlib import Path

from metagente_luna_s3.interpret import interpret
from metagente_luna_s4.runner import execute

OPERATIONS = [
    ("MGL5-INF-0105", "Ordenar registros por edad conservando orden entre edades iguales."),
    ("MGL5-INF-0106", "Ordenar 10.000 enteros en orden descendente."),
    ("MGL5-INF-0109", "Ejecutar push, pop y peek con secuencia predefinida."),
    ("MGL5-INF-0110", "Encolar A, B, C y desencolar tres veces."),
    ("MGL5-INF-0111", "Insertar y eliminar nodos en cabeza, centro y cola."),
    ("MGL5-INF-0112", "Insertar 8, 3, 10, 1, 6, 14 en árbol BST y obtener inorder."),
    ("MGL5-INF-0115", "Recorrer grafo con ciclo usando DFS."),
    ("MGL5-INF-0113", "Insertar secuencia ascendente de 1 a 1.000 en árbol AVL balanceado."),
    ("MGL5-INF-0116", "Calcular ruta mínima en grafo con pesos no negativos usando Dijkstra."),
    ("MGL5-INF-0117", "Dijkstra: introducir arista negativa y rechazarla."),
    ("MGL5-INF-0118", "Detectar ciclo negativo alcanzable con Bellman-Ford."),
    ("MGL5-INF-0119", "Medir búsqueda lineal en arreglos de tamaño 1.000, 2.000 y 4.000."),
    ("MGL5-INF-0114", "Buscar ruta en grafo de seis nodos conocido."),
    ("MGL5-INF-0609", "Multiplicar matrices 2×3 y 3×2 conocidas."),
    ("MGL5-INF-0611", "Calcular determinante de matriz 3×3 de referencia."),
    ("MGL5-INF-0632", "Calcular media móvil de ventana 3 sobre fixture."),
]

_FIXTURE = json.loads(
    (Path(__file__).resolve().parents[2] / "fixtures" / "derived_parameters.json").read_text(encoding="utf-8")
)

# The source-derived fixture fixes the seed and count; the registered
# descending_seed capability deterministically materializes the 10,000 integers.
_TEN_THOUSAND = _FIXTURE["ten-thousand"]

# Only candidates whose source-derived fixture and registered capability are
# complete are exposed to the C05 plan compiler. Other interpreter candidates
# remain visible in the coverage matrix as blocked/ambiguous.
CASES = [
    # C05 additions: fixture-backed graph, tree, list, queue and complexity plans.
    {
        "case_id": "MGL5-INF-0106",
        "capability_id": "descending_seed",
        "arguments": {"seed": _TEN_THOUSAND["seed"], "count": _TEN_THOUSAND["count"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#ten-thousand; seed/count drive deterministic integer generation",
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
    {
        "case_id": "MGL5-INF-0111",
        "capability_id": "linked_list",
        "arguments": {"operations": _FIXTURE["linked-list"]["operations"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#linked-list; head/middle/tail operations",
    },
    {
        "case_id": "MGL5-INF-0115",
        "capability_id": "dfs_graph",
        "arguments": {"nodes": _FIXTURE["dfs-cycle"]["nodes"], "edges": _FIXTURE["dfs-cycle"]["edges"], "start": _FIXTURE["dfs-cycle"]["start"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#dfs-cycle; directed cycle with reachable tail",
    },
    {
        "case_id": "MGL5-INF-0116",
        "capability_id": "dijkstra",
        "arguments": {"nodes": _FIXTURE["dijkstra-positive"]["nodes"], "edges": _FIXTURE["dijkstra-positive"]["edges"], "start": _FIXTURE["dijkstra-positive"]["start"], "target": _FIXTURE["dijkstra-positive"]["target"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#dijkstra-positive; nonnegative weighted graph",
    },
    {
        "case_id": "MGL5-INF-0117",
        "capability_id": "dijkstra",
        "arguments": {"nodes": _FIXTURE["dijkstra-negative"]["nodes"], "edges": _FIXTURE["dijkstra-negative"]["edges"], "start": _FIXTURE["dijkstra-negative"]["start"], "target": _FIXTURE["dijkstra-negative"]["target"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#dijkstra-negative; negative edge rejection",
    },
    {
        "case_id": "MGL5-INF-0118",
        "capability_id": "bellman_ford_cycle",
        "arguments": {"nodes": _FIXTURE["bellman-negative-cycle"]["nodes"], "edges": _FIXTURE["bellman-negative-cycle"]["edges"], "start": _FIXTURE["bellman-negative-cycle"]["start"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#bellman-negative-cycle; reachable negative cycle",
    },
    {
        "case_id": "MGL5-INF-0114",
        "capability_id": "shortest_path",
        "arguments": {key: _FIXTURE["bfs-six-node"][key] for key in ("nodes", "edges", "start", "target")},
        "fixture_provenance": "FIXTURE:derived_parameters.json#bfs-six-node; six-node directed graph with tied shortest paths",
    },
    {
        "case_id": "MGL5-INF-0609",
        "capability_id": "matrix_multiply",
        "arguments": {"left": _FIXTURE["matrix-product"]["left"], "right": _FIXTURE["matrix-product"]["right"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#matrix-product; 2x3 by 3x2 integer matrices",
    },
    {
        "case_id": "MGL5-INF-0611",
        "capability_id": "determinant_3x3",
        "arguments": {"matrix": _FIXTURE["determinant-reference"]["matrix"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#determinant-reference; expected determinant -306",
    },
    {
        "case_id": "MGL5-INF-0632",
        "capability_id": "moving_average_c05",
        "arguments": {"values": _FIXTURE["moving-window"]["values"], "window": _FIXTURE["moving-window"]["window"]},
        "fixture_provenance": "FIXTURE:derived_parameters.json#moving-window; explicit six values, window 3",
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
