"""Additive command wiring. Does not add commands or reassign agents or engines.

Frame identities stay distinct. A route may combine them; it may not merge them.
"""
from __future__ import annotations

import re
from typing import Any, Sequence

FRAME_ORDER = (
    "Jewish", "Allegorical", "Antiochene_Literal", "Patristic", "Medieval",
    "Reformation", "Protestant_Orthodox", "Rationalist", "Historical_Critical",
    "Liberal_Theological", "Theological_Existential", "New_Hermeneutics",
    "Evangelical_Grammatical_Historical", "Integrative_Multidisciplinary_Meta_Hermeneutics",
    "Calvinist", "Lutheran", "Zwinglian", "Arminian",
)

THEOLOGICAL_CONFIGURATION = {
    "identity": "REFORMED_TULIP_SOLA_SCRIPTURA_SUPREME",
    "role": "SYSTEM_DOCTRINAL_CONFIGURATION",
    "does_not_collapse_frames": True,
}

COGNITIVE_STAGES = (
    "RECEPTION", "INTENT", "CONTEXT", "RETRIEVAL", "SELECTION", "PLAN",
    "EXECUTION", "VALIDATION", "COHERENCE", "PROVENANCE", "ERRORS",
    "CORRECTION", "MEMORY_UPDATE", "METACOGNITION", "CONTINUITY",
)

COGNITIVE_CICD_POLICY = "COGNITIVE_CICD_ALWAYS_ON_PER_USER_REQUEST=TRUE"
HISTORICAL_AUTOMATIC_ACTIVATION = "AUTOMATIC_ACTIVATION=FORBIDDEN"

# Eight CFE families. Ranges are disjoint. Commands combine families; they do not fuse them.
CFE_FAMILIES = (
    {"id": "LANGUAGE_REASONING", "range": (1, 10), "label": "Language Reasoning"},
    {"id": "RETRIEVAL_SEMANTIC", "range": (11, 20), "label": "Retrieval Semantic"},
    {"id": "KNOWLEDGE_GRAPH", "range": (21, 30), "label": "Knowledge Graph"},
    {"id": "ONTOLOGY_INFERENCE", "range": (31, 40), "label": "Ontology Inference"},
    {"id": "RULE_VALIDATION", "range": (41, 50), "label": "Rule Validation"},
    {"id": "HERMENEUTIC_FORMALIZATION", "range": (51, 60), "label": "Hermeneutic Formalization"},
    {"id": "PROVENANCE_TRACE", "range": (61, 70), "label": "Provenance Trace"},
    {"id": "CONSENSUS_CERTIFICATION", "range": (71, 74), "label": "Consensus Certification"},
)

# Added beside the historical extension_families catalog. That catalog is not rewritten.
COMMAND_CFE = {
    "/help": ("PROVENANCE_TRACE", "CONSENSUS_CERTIFICATION"),
    "/play PT": ("LANGUAGE_REASONING", "RETRIEVAL_SEMANTIC", "RULE_VALIDATION", "HERMENEUTIC_FORMALIZATION"),
    "/play PA": ("KNOWLEDGE_GRAPH", "ONTOLOGY_INFERENCE", "RULE_VALIDATION", "PROVENANCE_TRACE"),
    "/play DCI": ("RETRIEVAL_SEMANTIC", "RULE_VALIDATION", "PROVENANCE_TRACE", "CONSENSUS_CERTIFICATION"),
    "/play DCIL": ("LANGUAGE_REASONING", "RETRIEVAL_SEMANTIC", "RULE_VALIDATION", "HERMENEUTIC_FORMALIZATION", "PROVENANCE_TRACE", "CONSENSUS_CERTIFICATION"),
    "/play traductor": ("LANGUAGE_REASONING", "RETRIEVAL_SEMANTIC", "RULE_VALIDATION", "PROVENANCE_TRACE", "CONSENSUS_CERTIFICATION"),
    "/play e": ("RULE_VALIDATION", "HERMENEUTIC_FORMALIZATION", "PROVENANCE_TRACE", "CONSENSUS_CERTIFICATION"),
    "/play ema": ("HERMENEUTIC_FORMALIZATION", "PROVENANCE_TRACE", "CONSENSUS_CERTIFICATION"),
    "/play p": ("RULE_VALIDATION", "PROVENANCE_TRACE", "CONSENSUS_CERTIFICATION"),
    "/play c": ("LANGUAGE_REASONING", "RULE_VALIDATION", "HERMENEUTIC_FORMALIZATION", "CONSENSUS_CERTIFICATION"),
    "/play cp": ("RETRIEVAL_SEMANTIC", "KNOWLEDGE_GRAPH", "ONTOLOGY_INFERENCE", "RULE_VALIDATION", "HERMENEUTIC_FORMALIZATION", "PROVENANCE_TRACE", "CONSENSUS_CERTIFICATION"),
    "/play MA": tuple(row["id"] for row in CFE_FAMILIES),
    "/play H": ("RULE_VALIDATION", "HERMENEUTIC_FORMALIZATION", "PROVENANCE_TRACE", "CONSENSUS_CERTIFICATION"),
    "/play AE": ("KNOWLEDGE_GRAPH", "ONTOLOGY_INFERENCE", "RULE_VALIDATION", "PROVENANCE_TRACE"),
}

_PROFILES = {
    "Jewish": ("Peshat primero.", "El derash se rotula aparte.", "Texto hebreo y su recepción judía.", "No absorbe el marco alegórico."),
    "Allegorical": ("La alegoría se declara.", "No sustituye el sentido primero.", "Textos que el pedido nombra como alegóricos.", "No se aplica a una traducción cotidiana."),
    "Antiochene_Literal": ("Gramática e historia del pasaje.", "Antes de cualquier síntesis.", "Narrativa y discurso en su contexto.", "No hereda el método patrístico."),
    "Patristic": ("La cita patrística se aporta.", "No reemplaza el texto.", "Recepción de los padres cuando el pedido la pide.", "No se vuelve el léxico del pasaje."),
    "Medieval": ("Cada sentido medieval se nombra.", "Los sentidos no se promedian.", "Comentario medieval explícito.", "No se confunde con la Reforma."),
    "Reformation": ("Lengua y contexto inmediato.", "La tradición citada va después.", "Texto y confesión de la Reforma cuando se piden.", "No anula a Jewish ni a Antiochene."),
    "Protestant_Orthodox": ("La confesión se rotula como recepción.", "No se presenta como léxico.", "Formulaciones de la ortodoxia protestante pedidas.", "No equivale a Rationalist."),
    "Rationalist": ("Premisa, afirmación y hueco.", "La evidencia ausente queda visible.", "Argumento que pide examen racional.", "No llena el silencio del texto."),
    "Historical_Critical": ("Fecha, género y audiencia.", "Se exigen antes del dato histórico.", "Preguntas de historia y composición.", "No es el método gramatical-histórico evangélico."),
    "Liberal_Theological": ("La reconstrucción moderna se rotula.", "No se presenta como sentido original.", "Debate teológico moderno pedido.", "No se funde con Patristic."),
    "Theological_Existential": ("La situación del lector queda aparte.", "No se funde con la del texto.", "Pregunta existencial explícita.", "No redefine el significado textual."),
    "New_Hermeneutics": ("La pregunta del lector se distingue.", "No se confunde con la respuesta del texto.", "Diálogo hermenéutico pedido.", "No reemplaza la observación."),
    "Evangelical_Grammatical_Historical": ("Léxico, gramática y contexto controlan.", "La interpretación se separa del significado.", "Texto bíblico sin otro marco explícito.", "No dispara los otros diecisiete."),
    "Integrative_Multidisciplinary_Meta_Hermeneutics": ("Las disciplinas se comparan.", "No se promedian.", "Pedido de comparación entre marcos.", "No autoriza a mezclarlos en uno."),
    "Calvinist": ("Se aplica solo si fue pedido.", "No es la configuración por defecto de toda tarea.", "Comparación o encargo calvinista.", "No subordina a los otros diecisiete."),
    "Lutheran": ("Ley y evangelio no se proyectan solos.", "Hace falta evidencia textual.", "Encargo luterano explícito.", "No se copia dentro de Zwinglian."),
    "Zwinglian": ("La tesis queda limitada.", "Solo la comparación pedida.", "Encargo zwingliano explícito.", "No se extiende al texto cotidiano."),
    "Arminian": ("El silencio del texto no es prueba.", "La inferencia se rotula.", "Encargo arminiano explícito.", "No se infiere desde Calvinist."),
}

_FRAME_PATTERNS = (
    ("Jewish", re.compile(r"\b(jewish|jud[ií]o|peshat)\b", re.I)),
    ("Allegorical", re.compile(r"\b(allegorical|aleg[oó]ric[oa])\b", re.I)),
    ("Antiochene_Literal", re.compile(r"\b(antiochene_literal|antioqueno)\b", re.I)),
    ("Patristic", re.compile(r"\b(patristic|patr[ií]stic[oa])\b", re.I)),
    ("Medieval", re.compile(r"\b(medieval|escol[aá]stic[oa])\b", re.I)),
    ("Reformation", re.compile(r"\b(reformation|reforma protestante)\b", re.I)),
    ("Protestant_Orthodox", re.compile(r"\b(protestant_orthodox|ortodoxia protestante)\b", re.I)),
    ("Rationalist", re.compile(r"\b(rationalist|racionalista)\b", re.I)),
    ("Historical_Critical", re.compile(r"\b(historical_critical|hist[oó]rico-cr[ií]tic[oa])\b", re.I)),
    ("Liberal_Theological", re.compile(r"\b(liberal_theological|teolog[ií]a liberal)\b", re.I)),
    ("Theological_Existential", re.compile(r"\b(theological_existential|existencial)\b", re.I)),
    ("New_Hermeneutics", re.compile(r"\b(new_hermeneutics|nueva hermen[eé]utica)\b", re.I)),
    ("Evangelical_Grammatical_Historical", re.compile(r"\b(evangelical_grammatical_historical|gramatical-hist[oó]ric[oa])\b", re.I)),
    ("Integrative_Multidisciplinary_Meta_Hermeneutics", re.compile(r"\b(integrative_multidisciplinary_meta_hermeneutics|meta-hermen[eé]utica)\b", re.I)),
    ("Calvinist", re.compile(r"\b(calvinist|calvinista)\b", re.I)),
    ("Lutheran", re.compile(r"\b(lutheran|luteran[oa])\b", re.I)),
    ("Zwinglian", re.compile(r"\b(zwinglian|zwinglian[oa])\b", re.I)),
    ("Arminian", re.compile(r"\b(arminian|arminian[oa])\b", re.I)),
)
_EXHAUSTIVE = re.compile(r"\b(18 marcos|dieciocho marcos|comparaci[oó]n exhaustiva|evaluaci[oó]n integral)\b", re.I)
_BIBLICAL = re.compile(r"\b(biblia|escrituras?|vers[ií]culo|evangelio|tor[aá]h?|salmo)\b", re.I)
_ANCIENT = re.compile(r"\b(hebreo|arameo|griego koin[eé]|lat[ií]n cl[aá]sico|acadio|ugar[ií]tico)\b", re.I)
_SPECIALIZED = re.compile(r"\b(terminolog[ií]a|jurisprudencia|especificaci[oó]n t[eé]cnica)\b", re.I)
_AUDIO = re.compile(r"\b(audio|voz|transcrib\w*)\b", re.I)

HERMENEUTIC_SEQUENCE = (
    "TEXT", "OBSERVATION", "LINGUISTIC_ANALYSIS", "CONTEXT",
    "HISTORICAL_CULTURAL_ANALYSIS", "INFERENCE", "INTERPRETATION",
    "DOCTRINAL_SYNTHESIS", "VALIDATION",
)
HERMENEUTIC_CONTROLS = (
    "EISEGESIS", "PROOF_TEXTING", "ANACHRONISM", "LEXICAL_FALLACY",
    "SEMANTIC_OVERLOAD", "CONTEXT_DISPLACEMENT",
)


def frame_profiles() -> dict[str, dict[str, str]]:
    profiles = {}
    for name in FRAME_ORDER:
        principle, method, texts, difference = _PROFILES[name]
        profiles[name] = {
            "frame_id": name,
            "principles": principle,
            "method": method,
            "applicable_texts": texts,
            "requirements": "Lengua, historia y contexto del propio marco; no los de otro.",
            "criteria": "El significado textual queda separado de la interpretación.",
            "expected_results": "Observación, inferencia e interpretación permanecen separados.",
            "limits": difference,
            "difference_from_others": difference,
        }
    return profiles


def classify_translation(text: str) -> str:
    if _AUDIO.search(text or ""):
        return "TRANSCRIPTION_THEN_TRANSLATION"
    if _BIBLICAL.search(text or ""):
        return "BIBLICAL_LINGUISTIC_PLUS_HERMENEUTIC_HANDOFF"
    if _ANCIENT.search(text or ""):
        return "ANCIENT_LINGUISTIC"
    if _SPECIALIZED.search(text or ""):
        return "SPECIALIZED_TERMINOLOGICAL"
    return "GENERAL"


def select_frames(text: str, *, command: str | None) -> dict[str, Any]:
    if command == "/play traductor" and classify_translation(text) == "GENERAL":
        return {"mode": "NOT_APPLICABLE", "primary": None, "secondary": []}
    matched = [name for name, pattern in _FRAME_PATTERNS if pattern.search(text or "")]
    if _EXHAUSTIVE.search(text or ""):
        primary = matched[0] if matched else FRAME_ORDER[0]
        secondary = [name for name in FRAME_ORDER if name != primary]
        return {"mode": "EXHAUSTIVE_18", "primary": primary, "secondary": secondary}
    if len(matched) > 1:
        return {"mode": "AMBIGUOUS", "primary": None, "secondary": [], "candidates": matched}
    if len(matched) == 1:
        return {"mode": "PRIMARY_ONLY", "primary": matched[0], "secondary": []}
    if command == "/play H" and _BIBLICAL.search(text or ""):
        return {
            "mode": "PRIMARY_ONLY",
            "primary": "Evangelical_Grammatical_Historical",
            "secondary": [],
            "default_reason": "BIBLICAL_TEXT_WITHOUT_EXPLICIT_FRAME",
        }
    if command == "/play H":
        return {"mode": "BLOCKED_FRAME_NOT_DETERMINED", "primary": None, "secondary": []}
    return {"mode": "NOT_APPLICABLE", "primary": None, "secondary": []}


def phase1_report(command: str | None, text: str, engines: Sequence[str]) -> dict[str, Any]:
    modality = classify_translation(text) if command == "/play traductor" else None
    frames = select_frames(text, command=command)
    engine_list = list(engines)
    e11_in_route = "E11" in engine_list
    handoff = modality == "BIBLICAL_LINGUISTIC_PLUS_HERMENEUTIC_HANDOFF"
    errors = []
    if handoff and e11_in_route:
        errors.append("E11_SILENTLY_PRESENT_IN_TRADUCTOR_ROUTE")
    if frames["mode"] == "AMBIGUOUS":
        errors.append("FRAME_SELECTION_AMBIGUOUS")
    if frames["mode"] == "BLOCKED_FRAME_NOT_DETERMINED":
        errors.append("FRAME_SELECTION_BLOCKED_FRAME_NOT_DETERMINED")
    return {
        "schema": "LOUKSNA1_PHASE1_COMMAND_WIRING/1.0",
        "cognitive_cicd": "ALWAYS_ON_PER_USER_REQUEST",
        "cognitive_cicd_policy": COGNITIVE_CICD_POLICY,
        "historical_automatic_activation_retained": HISTORICAL_AUTOMATIC_ACTIVATION,
        "privileged_operations_authorized": False,
        "stages": list(COGNITIVE_STAGES),
        "hermeneutic_sequence": list(HERMENEUTIC_SEQUENCE),
        "hermeneutic_controls": list(HERMENEUTIC_CONTROLS),
        "translation_modality": modality,
        "frames": frames,
        "theological_configuration": THEOLOGICAL_CONFIGURATION,
        "cfe_families": list(COMMAND_CFE.get(command, ())),
        "engines_unchanged": True,
        "e11_in_command_route": e11_in_route,
        "e11_executed": False,
        "hermeneutic_handoff_command": "/play H" if handoff else None,
        "memory_stores": 1,
        "memory_physical_domain": "D06_SISTEMA_INTELIGENTE",
        "errors": errors,
        "certification": "NOT_GRANTED",
    }
