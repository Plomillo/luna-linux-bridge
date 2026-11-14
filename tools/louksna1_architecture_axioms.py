"""Architecture-axiom consistency. This is not a proof of natural-language sentences.

Foundations keep their own identity. A command may combine them. It may not fuse them.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

EXPECTED_ROUTES = (
    ("/help", ("Luna",), ("E13", "E14", "E15")),
    ("/play PT", ("Luna", "Katya"), ("E01", "E02", "E11", "E12", "E13")),
    ("/play PA", ("Luna", "Ancapi"), ("E06", "E07", "E08", "E09", "E10", "E12", "E13", "E14")),
    ("/play DCI", ("Luna", "Josefina"), ("E03", "E04", "E05", "E09", "E11", "E12", "E13", "E14")),
    ("/play DCIL", ("Luna", "Josefina", "Katya"), ("E01", "E02", "E03", "E04", "E05", "E09", "E11", "E12", "E13", "E14", "E15")),
    ("/play traductor", ("Luna", "Katya"), ("E01", "E02", "E03", "E04", "E05", "E12", "E13", "E14", "E15")),
    ("/play e", ("Luna", "Josefina"), ("E11", "E12", "E13", "E14", "E15")),
    ("/play ema", ("Luna", "Josefina", "Katya"), ("E11", "E12", "E13", "E14", "E15")),
    ("/play p", ("Luna", "Ancapi"), ("E10", "E12", "E13", "E14", "E15")),
    ("/play c", ("Luna", "Katya"), ("E01", "E02", "E09", "E12", "E13", "E15")),
    ("/play cp", ("Luna", "Josefina", "Katya"), ("E03", "E05", "E06", "E09", "E11", "E12", "E13", "E14", "E15")),
    ("/play MA", ("Luna",), tuple(f"E{i:02d}" for i in range(1, 16))),
    ("/play H", ("Luna", "Josefina"), ("E11", "E12", "E13", "E14", "E15")),
    ("/play AE", ("Luna", "Ancapi"), ("E06", "E07", "E08", "E09", "E10", "E12", "E13", "E14", "E15")),
)

ENGINE_NAMES = {
    "E01": "LLM", "E02": "NLP", "E03": "RAG", "E04": "EMBEDDINGS", "E05": "VECTOR_SEARCH",
    "E06": "KNOWLEDGE_GRAPH", "E07": "RDF", "E08": "OWL", "E09": "SEMANTIC_INFERENCE",
    "E10": "RULE_ENGINE", "E11": "HERMENEUTIC", "E12": "FORMALIZATION", "E13": "VALIDATION",
    "E14": "PROVENANCE", "E15": "CONSENSUS",
}

DOMAIN_DIRS = (
    "1. Cerebro",
    "2. Orquestación",
    "3. Transcripción",
    "4. Traductor Inteligente",
    "5. Inteligencia documental",
    "6. Sistema Inteligente",
)

PROFILE_FIELDS = (
    "principles", "method", "applicable_texts", "requirements", "criteria",
    "expected_results", "limits", "difference_from_others",
)


def _load(runtime: Path, name: str):
    path = runtime / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_MISSING:" + name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_architecture(repo: Path) -> dict:
    problems: list[str] = []
    runtime = repo / "cajita-luna-runtime"
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    try:
        wiring = _load(runtime, "cajita_command_wiring")
        router = _load(runtime, "cajita_router")
    except Exception as exc:
        return {"status": "FAIL", "reason": type(exc).__name__ + ":" + str(exc)[:180], "problems": [str(exc)[:180]], "establishes_architecture_axioms": False}

    live = [(row["command"], tuple(row["agents"]), tuple(row["engines"])) for row in router.ROUTES]
    if live != list(EXPECTED_ROUTES):
        problems.append("ROUTE_MATRIX_DIVERGED")
    if len({row[0] for row in EXPECTED_ROUTES}) != 14:
        problems.append("COMMAND_IDENTITY_NOT_UNIQUE")
    if any(row[1][0] != "Luna" for row in EXPECTED_ROUTES):
        problems.append("LUNA_MISSING_FROM_ROUTE")

    families = list(wiring.CFE_FAMILIES)
    spans = []
    for row in families:
        start, end = row["range"]
        if start > end:
            problems.append("CFE_RANGE_INVERTED:" + row["id"])
        spans.append((start, end, row["id"]))
    spans.sort()
    for (a1, a2, left), (b1, b2, right) in zip(spans, spans[1:]):
        if b1 <= a2:
            problems.append(f"CFE_FAMILIES_OVERLAP:{left}:{right}")
    if [row["id"] for row in families] != list(wiring.COMMAND_CFE["/play MA"]):
        problems.append("MA_DOES_NOT_COMBINE_EVERY_CFE_FAMILY")
    if set(wiring.COMMAND_CFE) != {row[0] for row in EXPECTED_ROUTES}:
        problems.append("CFE_BINDING_COMMAND_SET_MISMATCH")

    profiles = wiring.frame_profiles()
    if tuple(profiles) != wiring.FRAME_ORDER or len(profiles) != 18:
        problems.append("FRAME_SET_MISMATCH")
    methods = [profiles[name]["method"] for name in profiles]
    if len(set(methods)) != 18:
        problems.append("FRAME_METHODS_OVERLAP")
    for name, profile in profiles.items():
        missing = [field for field in PROFILE_FIELDS if not profile.get(field)]
        if missing:
            problems.append("FRAME_PROFILE_THIN:" + name)
        if name in profile["method"]:
            problems.append("FRAME_METHOD_COLLAPSES_IDENTITY:" + name)

    ordinary = wiring.select_frames("una carta cotidiana", command="/play traductor")
    if ordinary["mode"] != "NOT_APPLICABLE" or ordinary["primary"] is not None:
        problems.append("ORDINARY_TRANSLATION_ACTIVATED_HERMENEUTICS")
    exhaustive = wiring.select_frames("comparación exhaustiva de los 18 marcos", command="/play H")
    if exhaustive["mode"] != "EXHAUSTIVE_18" or exhaustive["primary"] in exhaustive["secondary"] or len(exhaustive["secondary"]) != 17:
        problems.append("EXHAUSTIVE_COMPARISON_COLLAPSED_FRAMES")
    ambiguous = wiring.select_frames("calvinista y luterano", command="/play H")
    if ambiguous["mode"] != "AMBIGUOUS" or ambiguous["primary"] is not None:
        problems.append("AMBIGUOUS_FRAMES_WERE_MERGED")

    for folder in DOMAIN_DIRS:
        path = runtime / folder
        if not path.is_dir():
            problems.append("DOMAIN_MISSING:" + folder)
    memories = [path for path in runtime.rglob("Memoria Gobernada") if path.is_dir()]
    if len(memories) != 1 or "6. Sistema Inteligente" not in memories[0].as_posix():
        problems.append("GOVERNED_MEMORY_DUPLICATED_OR_MOVED")

    if wiring.COGNITIVE_CICD_POLICY != "COGNITIVE_CICD_ALWAYS_ON_PER_USER_REQUEST=TRUE":
        problems.append("COGNITIVE_CICD_NOT_ALWAYS_ON")
    if wiring.HISTORICAL_AUTOMATIC_ACTIVATION != "AUTOMATIC_ACTIVATION=FORBIDDEN":
        problems.append("HISTORICAL_ACTIVATION_RULE_DROPPED")

    engines = {row["id"]: row["name"] for row in router.ROUTING_REGISTRY.get("engine_registry", [])}
    if engines != ENGINE_NAMES:
        problems.append("ENGINE_REGISTRY_DIVERGED")

    quickjs = runtime / "6. Sistema Inteligente" / "Consola" / "quickjs-linux-x86_64-2026-06-04" / "qjs"
    if not quickjs.is_file():
        problems.append("QUICKJS_BINARY_MISSING")

    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "frame_count": len(profiles),
        "command_count": len(live),
        "cfe_family_count": len(families),
        "memory_store_count": len(memories),
        "natural_language_propositions": "NOT_ESTABLISHED",
        "establishes_architecture_axioms": not problems,
    }
