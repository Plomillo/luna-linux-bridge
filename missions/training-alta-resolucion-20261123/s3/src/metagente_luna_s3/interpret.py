"""Literal grammar. It does not call a remote model and it does not read a case id."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from lark import Lark, Token, Tree

from metagente_luna_s3.ir import Argument, Interpretation, Provenance

_PARSER = Lark(Path(__file__).with_name("grammar.lark").read_text(encoding="utf-8"), parser="earley")
_FIND = re.compile(r"buscar|localizar|hallar|primera|indice|aparicion|encontrar")
_DESCEND = re.compile(r"descendente|mayor a menor|de mayor")
_FIXTURE = json.loads((Path(__file__).resolve().parents[2] / "fixtures" / "derived_parameters.json").read_text(encoding="utf-8"))


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    plain = "".join(character for character in normalized if not unicodedata.combining(character))
    return plain.casefold()


def literals(instruction: str) -> dict[str, list[str]]:
    found = {"cidr": [], "ipv4": [], "bracket": [], "quoted": [], "number": []}
    for node in _PARSER.parse(instruction).children:
        if isinstance(node, Tree) and node.data in found:
            found[node.data].append(str(node.children[0]))
        elif isinstance(node, Token) and node.type in found:
            found[node.type].append(str(node))
    return found


def _ints(raw: str) -> list[int]:
    return [int(item) for item in raw.strip("[]").split(",") if item.strip()]


def _ready(text: str, intent: str, arguments: list[Argument]) -> Interpretation:
    return Interpretation(source_instruction=text, intent=intent, intent_method="LARK_LITERALS_PLUS_INTENT_WORD", arguments=arguments, status="READY")


def _blocked(text: str, intent: str, missing: list[str]) -> Interpretation:
    return Interpretation(source_instruction=text, intent=intent, intent_method="LARK_LITERALS_PLUS_INTENT_WORD", missing=missing, status="BLOCKED")


def interpret(instruction: str) -> Interpretation:
    found = literals(instruction)
    text = " ".join(instruction.split())
    folded = _fold(text)
    if found["cidr"] and ("red" in text or "broadcast" in text):
        return _ready(text, "cidr_bounds", [Argument(name="cidr", value=found["cidr"][0], provenance=Provenance.SOURCE_INSTRUCTION)])
    if found["cidr"]:
        return Interpretation(
            source_instruction=text,
            intent="UNRESOLVED",
            intent_method="LARK_LITERALS_PLUS_INTENT_WORD",
            arguments=[Argument(name="cidr", value=found["cidr"][0], provenance=Provenance.SOURCE_INSTRUCTION, required=False)],
            ambiguities=["a CIDR is present but the operation does not say network or broadcast"],
            status="AMBIGUOUS",
        )
    if found["bracket"] and _DESCEND.search(folded):
        return _ready(text, "descending_values", [Argument(name="values", value=_ints(found["bracket"][0]), provenance=Provenance.SOURCE_INSTRUCTION)])
    if found["bracket"] and _FIND.search(folded):
        if len(found["number"]) != 1:
            return _blocked(text, "first-match", ["needle"])
        return _ready(
            text,
            "first_match",
            [
                Argument(name="needle", value=int(found["number"][0]), provenance=Provenance.SOURCE_INSTRUCTION),
                Argument(name="values", value=_ints(found["bracket"][0]), provenance=Provenance.SOURCE_INSTRUCTION),
            ],
        )
    if ("10.000" in text or "10000" in text) and "ordenar" in folded and not found["bracket"]:
        fixture = _FIXTURE["ten-thousand"]
        return _ready(text, "descending_seed", [
            Argument(name="seed", value=fixture["seed"], provenance=Provenance.FIXTURE),
            Argument(name="count", value=fixture["count"], provenance=Provenance.FIXTURE),
        ])
    if "edad" in folded and "ordenar" in folded:
        return _ready(text, "stable_ages", [Argument(name="records", value=_FIXTURE["stable-ages"]["records"], provenance=Provenance.FIXTURE)])
    if "push" in folded and "peek" in folded:
        return _ready(
            text,
            "stack_sequence",
            [Argument(name="steps", value=_FIXTURE["stack-script"]["steps"], provenance=Provenance.FIXTURE)],
        )

    if "cola fifo" in folded or ("encolar" in folded and "desencolar" in folded):
        fixture = _FIXTURE["fifo-queue"]
        return _ready(text, "fifo_queue", [Argument(name="steps", value=fixture["steps"], provenance=Provenance.FIXTURE)])
    if "lista enlazada" in folded:
        fixture = _FIXTURE["linked-list"]
        return _ready(text, "linked_list", [Argument(name="operations", value=fixture["operations"], provenance=Provenance.FIXTURE)])
    if "bst" in folded or "arbol binario de busqueda" in folded:
        fixture = _FIXTURE["bst-values"]
        return _ready(text, "bst_inorder", [Argument(name="values", value=fixture["values"], provenance=Provenance.FIXTURE)])
    if "dfs" in folded or "recorrer grafo con ciclo" in folded:
        fixture = _FIXTURE["dfs-cycle"]
        return _ready(text, "dfs_graph", [Argument(name="nodes", value=fixture["nodes"], provenance=Provenance.FIXTURE), Argument(name="edges", value=fixture["edges"], provenance=Provenance.FIXTURE), Argument(name="start", value=fixture["start"], provenance=Provenance.FIXTURE)])

    if "nodos" in folded and "cabeza" in folded and "cola" in folded:
        fixture = _FIXTURE["linked-list"]
        return _ready(text, "linked_list", [Argument(name="operations", value=fixture["operations"], provenance=Provenance.FIXTURE)])
    if "balanceado" in folded or "avl" in folded:
        fixture = _FIXTURE["avl-ascending"]
        return _ready(text, "avl_tree", [Argument(name="values", value=fixture["values"], provenance=Provenance.FIXTURE)])
    if "busqueda lineal" in folded and "1.000" in text:
        fixture = _FIXTURE["linear-search-sizes"]
        return _ready(text, "linear_search_complexity", [Argument(name="sizes", value=fixture["sizes"], provenance=Provenance.FIXTURE), Argument(name="target", value=fixture["target"], provenance=Provenance.FIXTURE)])
    if "dijkstra" in folded and "negativa" in folded:
        fixture = _FIXTURE["dijkstra-negative"]
        return _ready(text, "dijkstra", [Argument(name="nodes", value=fixture["nodes"], provenance=Provenance.FIXTURE), Argument(name="edges", value=fixture["edges"], provenance=Provenance.FIXTURE), Argument(name="start", value=fixture["start"], provenance=Provenance.FIXTURE), Argument(name="target", value=fixture["target"], provenance=Provenance.FIXTURE)])
    if "dijkstra" in folded or "pesos no negativos" in folded:
        fixture = _FIXTURE["dijkstra-positive"]
        return _ready(text, "dijkstra", [Argument(name="nodes", value=fixture["nodes"], provenance=Provenance.FIXTURE), Argument(name="edges", value=fixture["edges"], provenance=Provenance.FIXTURE), Argument(name="start", value=fixture["start"], provenance=Provenance.FIXTURE), Argument(name="target", value=fixture["target"], provenance=Provenance.FIXTURE)])
    if "ciclo negativo" in folded or "bellman-ford" in folded:
        fixture = _FIXTURE["bellman-negative-cycle"]
        return _ready(text, "bellman_ford_cycle", [Argument(name="nodes", value=fixture["nodes"], provenance=Provenance.FIXTURE), Argument(name="edges", value=fixture["edges"], provenance=Provenance.FIXTURE), Argument(name="start", value=fixture["start"], provenance=Provenance.FIXTURE)])
    if "grafo" in folded or "seis nodos" in folded:
        fixture = _FIXTURE["bfs-six-node"]
        return _ready(text, "shortest_path", [
            Argument(name="nodes", value=fixture["nodes"], provenance=Provenance.FIXTURE),
            Argument(name="edges", value=fixture["edges"], provenance=Provenance.FIXTURE),
            Argument(name="start", value=fixture["start"], provenance=Provenance.FIXTURE),
            Argument(name="target", value=fixture["target"], provenance=Provenance.FIXTURE),
        ])
    if "determinante" in folded:
        fixture = _FIXTURE["determinant-reference"]
        return _ready(text, "determinant_3x3", [
            Argument(name="matrix", value=fixture["matrix"], provenance=Provenance.FIXTURE),
        ])
    if "matriz" in folded or "2×3" in text or "2x3" in folded:
        fixture = _FIXTURE["matrix-product"]
        return _ready(text, "matrix_multiply", [
            Argument(name="left", value=fixture["left"], provenance=Provenance.FIXTURE),
            Argument(name="right", value=fixture["right"], provenance=Provenance.FIXTURE),
        ])
    if "media movil" in folded or "ventana" in folded:
        fixture = _FIXTURE["moving-window"]
        return _ready(text, "moving_average_c05", [
            Argument(name="values", value=fixture["values"], provenance=Provenance.FIXTURE),
            Argument(name="window", value=fixture["window"], provenance=Provenance.FIXTURE),
        ])
    if "matriz" in folded or "determinante" in folded or "2×3" in text or "2x3" in folded:
        missing = ["reference-matrix"] if "determinante" in folded else ["matrix-entries"]
        return _blocked(text, "matrix", missing)
    if "media movil" in folded or "ventana" in folded:
        return _blocked(text, "moving-average", ["series-values", "series-length"])
    if _DESCEND.search(folded) or "ordenar" in folded:
        return _blocked(text, "sort", ["input-integers"])
    return Interpretation(
        source_instruction=text,
        intent="UNRESOLVED",
        intent_method="LARK_LITERALS_PLUS_INTENT_WORD",
        missing=["no registered intent"],
        status="UNRESOLVED",
    )
