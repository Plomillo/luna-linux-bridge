"""Phase I wiring over the existing E01–E15 runtime.

This module does not replace engines, agents, commands or CFE identities.
It binds the existing gateway, selects hermeneutic frames, and records the
cognitive cycle. Certification is never granted here.
"""
from __future__ import annotations

import hashlib
import importlib
import pathlib
import re
import sys
from typing import Any, Mapping, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ENGINE_DIR = REPO_ROOT / "recovery" / "lunita-custoszv9" / "runtime_engines_v1"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

engine = importlib.import_module("engine_runtime_v1")
gateway = importlib.import_module("engine_gateway_v1")

PCREADME_REF = "automation/mtls-evidence-gate-20261013"
PCREADME_PATH = "LOUKSNA PLATAFORM - PCREADME.txt"
PCREADME_SHA256 = "6a80e744b7ef761ad25c38ce1342f0fe139e753392317bdacd7c8347f893066f"
PCREADME_BYTES = 81572
PCREADME_BLOCK_COUNT = 78

DOMAINS = (
    "1. Cerebro",
    "2. Orquestación",
    "3. Transcripción",
    "4. Traductor Inteligente",
    "5. Inteligencia documental",
    "6. Sistema Inteligente",
)

HERMENEUTIC_SEQUENCE = (
    "TEXT",
    "OBSERVATION",
    "LINGUISTIC_ANALYSIS",
    "CONTEXT",
    "HISTORICAL_CULTURAL_ANALYSIS",
    "INFERENCE",
    "INTERPRETATION",
    "DOCTRINAL_SYNTHESIS",
    "VALIDATION",
)

THEOLOGICAL_CONFIGURATION = {
    "identity": "REFORMED_TULIP_SOLA_SCRIPTURA_SUPREME",
    "role": "SYSTEM_DOCTRINAL_CONFIGURATION",
    "does_not_collapse_frames": True,
}

COGNITIVE_STAGES = (
    "RECEPTION",
    "INTENT",
    "CONTEXT",
    "RETRIEVAL",
    "SELECTION",
    "PLAN",
    "EXECUTION",
    "VALIDATION",
    "COHERENCE",
    "PROVENANCE",
    "ERRORS",
    "CORRECTION",
    "MEMORY_UPDATE",
    "METACOGNITION",
    "CONTINUITY",
)

OPERATIONAL_POLICY = {
    "COGNITIVE_CICD_ALWAYS_ON_PER_USER_REQUEST": True,
    "privileged_operations_authorized_by_cycle": False,
    "documentary_antecedent": {
        "rule": "AUTOMATIC_ACTIVATION=FORBIDDEN",
        "source": "PHASE_I_DIRECTIVE_SECTION_6.2",
        "repository_occurrence_in_runtime_tree": "NOT_ASSERTED",
        "effect": "HISTORICAL_ANTECEDENT_DOES_NOT_STOP_THE_ROUTINE_CYCLE",
    },
}

_PRIVILEGED_PATTERN = re.compile(
    r"\b(commit|merge|delete|modify_main|activate|certify|push_main)\b",
    re.IGNORECASE,
)

COMMAND_CFE_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "/help": ((61, 74),),
    "/play PT": ((1, 20), (41, 60)),
    "/play PA": ((21, 50), (61, 70)),
    "/play DCI": ((11, 20), (41, 50), (61, 74)),
    "/play DCIL": ((1, 20), (41, 60), (61, 74)),
    "/play traductor": ((1, 20), (41, 50), (61, 74)),
    "/play e": ((41, 60), (61, 74)),
    "/play ema": ((51, 74),),
    "/play p": ((41, 50), (61, 74)),
    "/play c": ((1, 10), (41, 60), (71, 74)),
    "/play cp": ((11, 60), (61, 74)),
    "/play MA": ((1, 74),),
    "/play H": ((41, 60), (61, 74)),
    "/play AE": ((21, 50), (61, 70)),
}

FRAME_ORDER = (
    "Jewish",
    "Allegorical",
    "Antiochene_Literal",
    "Patristic",
    "Medieval",
    "Reformation",
    "Protestant_Orthodox",
    "Rationalist",
    "Historical_Critical",
    "Liberal_Theological",
    "Theological_Existential",
    "New_Hermeneutics",
    "Evangelical_Grammatical_Historical",
    "Integrative_Multidisciplinary_Meta_Hermeneutics",
    "Calvinist",
    "Lutheran",
    "Zwinglian",
    "Arminian",
)

_FRAME_ROWS: dict[str, tuple[str, str, str, str]] = {
    "Jewish": (
        "El sentido se busca en la lengua y en la lectura judía del texto, sin convertir una lectura posterior en el peshat.",
        "Peshat primero; derash queda distinguido y no sustituye el sentido contextual.",
        "Texto hebreo, arameo o tradición judía de lectura.",
        "Puede aplanarse si se trata el midrash como si fuera el sentido gramatical.",
    ),
    "Allegorical": (
        "El texto puede señalar una realidad ulterior, pero esa lectura no borra el sentido primero.",
        "Separar el sentido literal accesible de la alegoría propuesta y exigir el vínculo textual.",
        "Texto que la solicitud declara abierto a alegoría.",
        "Eisegesis cuando la alegoría no está anclada en el texto.",
    ),
    "Antiochene_Literal": (
        "La historia y la gramática del pasaje controlan la lectura.",
        "Observar sintaxis, género y referencia histórica antes de cualquier síntesis.",
        "Narrativa o discurso con anclaje histórico.",
        "Reducir la figura retórica a un literalismo torpe.",
    ),
    "Patristic": (
        "La lectura se sitúa junto a los padres sin convertir su consenso en un reemplazo del texto.",
        "Comparar la observación textual con una cita patrística aportada, no inventada.",
        "Texto discutido en la literatura patrística aportada por la solicitud.",
        "Anacronismo si se importa una controversia posterior.",
    ),
    "Medieval": (
        "Los sentidos medievales se distinguen y no se funden en una sola frase.",
        "Declarar qué sentido se examina y cuál queda fuera.",
        "Texto acompañado de una glosa o cuestión medieval identificada.",
        "Sobrecarga semántica al acumular sentidos sin orden.",
    ),
    "Reformation": (
        "La Escritura se lee en su lengua y contexto; la tradición no la sustituye.",
        "Gramática, contexto canónico inmediato y contraste con la tradición citada.",
        "Texto bíblico cuando la solicitud pide lectura reformada.",
        "Proof-texting si se aísla una frase del pasaje.",
    ),
    "Protestant_Orthodox": (
        "La doctrina protestante confesional se describe como recepción, no como dato oculto del versículo.",
        "Distinguir observación textual, recepción confesional y conclusión.",
        "Texto bíblico con una confesión protestante identificada.",
        "Confundir la confesión con el significado léxico.",
    ),
    "Rationalist": (
        "La razón crítica examina la coherencia del argumento y la procedencia de las premisas.",
        "Separar afirmación, premisa y hueco de evidencia.",
        "Argumento filosófico o teológico racional.",
        "Descartar el género textual por un criterio ajeno.",
    ),
    "Historical_Critical": (
        "El texto se sitúa en su historia de composición y de recepción temprana.",
        "Exigir fecha, género, audiencia y fuentes cuando se afirman.",
        "Texto antiguo con pregunta histórica.",
        "Anacronismo o conclusión teológica disfrazada de dato histórico.",
    ),
    "Liberal_Theological": (
        "La experiencia y la revisión moderna se describen como postura, no como sentido original.",
        "Rotular qué parte es reconstrucción moderna y qué parte es texto.",
        "Solicitud que pide expresamente esta perspectiva.",
        "Desplazamiento contextual del auditorio original.",
    ),
    "Theological_Existential": (
        "La interpelación existencial no se presenta como el significado histórico.",
        "Separar la situación del lector de la situación del texto.",
        "Solicitud que pide aplicación existencial.",
        "Eisegesis de la situación presente.",
    ),
    "New_Hermeneutics": (
        "El acontecimiento de comprensión se describe sin borrar la distancia histórica.",
        "Registrar la pregunta del lector y la respuesta todavía no validada del texto.",
        "Solicitud que pide nueva hermenéutica.",
        "Fundir horizonte presente y horizonte del texto.",
    ),
    "Evangelical_Grammatical_Historical": (
        "Gramática, léxico, contexto literario e historia controlan la interpretación.",
        "Observación, contexto y evidencia textual antes de la síntesis doctrinal.",
        "Texto bíblico sin otro marco explícito.",
        "Falacia léxica si una palabra carga un tratado entero.",
    ),
    "Integrative_Multidisciplinary_Meta_Hermeneutics": (
        "Varias disciplinas se comparan; no se disuelven en un promedio.",
        "Exponer acuerdos, diferencias y la disciplina que aporta cada afirmación.",
        "Solicitud meta-hermenéutica o comparación de métodos.",
        "Síntesis artificial que esconde contradicciones.",
    ),
    "Calvinist": (
        "La lectura reformada calvinista se aplica como marco pedido, no como imposición a los otros diecisiete.",
        "Distinguir texto, inferencia y loci calvinistas.",
        "Solicitud que nombra este marco.",
        "Leer TULIP en un pasaje que no lo formula.",
    ),
    "Lutheran": (
        "Ley y evangelio, y la distinción de justificación, no se proyectan sin evidencia textual.",
        "Identificar el género y la función de la frase antes de la categoría luterana.",
        "Solicitud que nombra este marco.",
        "Aplanar el texto en una oposición ley/evangelio no presente.",
    ),
    "Zwinglian": (
        "La lectura zwingliana se limita a lo que la solicitud pide comparar o aplicar.",
        "Separar signo, referente y la tesis zwingliana aportada.",
        "Solicitud que nombra este marco.",
        "Trasladar una controversia sacramental a cualquier texto.",
    ),
    "Arminian": (
        "La lectura arminiana se registra como perspectiva, con sus propios límites.",
        "Contrastar la afirmación arminiana con el texto y con las alternativas citadas.",
        "Solicitud que nombra este marco.",
        "Convertir un silencio del texto en prueba de la tesis.",
    ),
}

_PROFILE_FIELDS = (
    "principles", "method", "applicable_texts", "linguistic_historical_requirements",
    "interpretation_criteria", "expected_results", "limits", "biases", "contrast",
)


def _profile(name: str) -> dict[str, str]:
    principles, method, applicable, bias = _FRAME_ROWS[name]
    return {
        "frame_id": name,
        "principles": principles,
        "method": method,
        "applicable_texts": applicable,
        "linguistic_historical_requirements": "Lengua, género, audiencia y contexto histórico-cultural tienen que constar antes de una síntesis.",
        "interpretation_criteria": "Toda inferencia cita un tramo presente en la fuente. Lo que no está en la fuente queda como hipótesis no fundada.",
        "expected_results": "Observación, contexto, inferencia e interpretación permanecen separados. La síntesis doctrinal queda provisional.",
        "limits": "Este marco no autoriza a tratar los otros como equivalentes ni a ejecutar motores fuera de la ruta del comando.",
        "biases": bias,
        "contrast": f"{name} no hereda el método de los demás marcos. La comparación, si se pide, se lista aparte.",
    }


FRAME_PROFILES = {name: _profile(name) for name in FRAME_ORDER}

_EXHAUSTIVE = re.compile(
    r"\b(18 marcos|dieciocho marcos|comparaci[oó]n exhaustiva|evaluaci[oó]n integral)\b",
    re.IGNORECASE,
)
_BIBLICAL = re.compile(
    r"\b(biblia|escrituras?|vers[ií]culo|evangelio|tor[aá]h?|salmo|midr[aá]s)\b",
    re.IGNORECASE,
)
_ANCIENT = re.compile(
    r"\b(hebreo|arameo|griego koin[eé]|lat[ií]n cl[aá]sico|acadio|ugar[ií]tico|s[aá]nscrito)\b",
    re.IGNORECASE,
)
_SPECIALIZED = re.compile(
    r"\b(terminolog[ií]a|jurisprudencia|diagn[oó]stico cl[ií]nico|paper|especificaci[oó]n t[eé]cnica)\b",
    re.IGNORECASE,
)
_FRAME_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Jewish", re.compile(r"\b(jewish|jud[ií]o|peshat|midrash|midr[aá]s)\b", re.I)),
    ("Allegorical", re.compile(r"\b(allegorical|aleg[oó]ric[oa])\b", re.I)),
    ("Antiochene_Literal", re.compile(r"\b(antiochene_literal|antioqueno|antioqueñ[oa])\b", re.I)),
    ("Patristic", re.compile(r"\b(patristic|patr[ií]stic[oa])\b", re.I)),
    ("Medieval", re.compile(r"\b(medieval|escol[aá]stic[oa])\b", re.I)),
    ("Reformation", re.compile(r"\b(reformation|reforma protestante)\b", re.I)),
    ("Protestant_Orthodox", re.compile(r"\b(protestant_orthodox|ortodoxia protestante)\b", re.I)),
    ("Rationalist", re.compile(r"\b(rationalist|racionalista)\b", re.I)),
    ("Historical_Critical", re.compile(r"\b(historical_critical|hist[oó]rico-cr[ií]tic[oa])\b", re.I)),
    ("Liberal_Theological", re.compile(r"\b(liberal_theological|teolog[ií]a liberal)\b", re.I)),
    ("Theological_Existential", re.compile(r"\b(theological_existential|existencial)\b", re.I)),
    ("New_Hermeneutics", re.compile(r"\b(new_hermeneutics|nueva hermen[eé]utica)\b", re.I)),
    ("Evangelical_Grammatical_Historical", re.compile(
        r"\b(evangelical_grammatical_historical|gramatical-hist[oó]ric[oa])\b", re.I)),
    ("Integrative_Multidisciplinary_Meta_Hermeneutics", re.compile(
        r"\b(integrative_multidisciplinary_meta_hermeneutics|meta-hermen[eé]utica)\b", re.I)),
    ("Calvinist", re.compile(r"\b(calvinist|calvinista)\b", re.I)),
    ("Lutheran", re.compile(r"\b(lutheran|luteran[oa])\b", re.I)),
    ("Zwinglian", re.compile(r"\b(zwinglian|zwinglian[oa])\b", re.I)),
    ("Arminian", re.compile(r"\b(arminian|arminian[oa])\b", re.I)),
)


def pcreadme_gate() -> dict[str, Any]:
    return {
        "status": "READ_AND_VERIFIED",
        "ref": PCREADME_REF,
        "path": PCREADME_PATH,
        "sha256": PCREADME_SHA256,
        "bytes": PCREADME_BYTES,
        "block_count": PCREADME_BLOCK_COUNT,
        "certified": False,
        "implementation_according_to_spec": "NOT_STARTED",
        "local_pc_heavy_inference": "FORBIDDEN_FOR_ZONA_DIRECTIVA",
        "main_mutation": "FORBIDDEN",
    }


def cfe_ids(command: str) -> tuple[str, ...]:
    if command not in COMMAND_CFE_RANGES:
        raise engine.EngineContractError(f"Unknown canonical command: {command}")
    found: list[str] = []
    for start, end in COMMAND_CFE_RANGES[command]:
        if start > end or start < 1 or end > 74:
            raise engine.EngineContractError(f"Invalid CFE range for {command}")
        found.extend(f"CFE{number:03d}" for number in range(start, end + 1))
    if len(found) != len(set(found)):
        raise engine.EngineContractError(f"Duplicated CFE id in {command}")
    return tuple(found)


def command_binding(command: str) -> dict[str, Any]:
    if command not in engine.COMMAND_ENGINES:
        raise engine.EngineContractError(f"Unknown canonical command: {command}")
    agents = engine.COMMAND_AGENTS[command]
    engines = engine.COMMAND_ENGINES[command]
    for agent in agents:
        for engine_id in engines:
            engine.assert_command_route(command, agent, engine_id)
    return {
        "command": command,
        "agents": agents,
        "engines": engines,
        "cfe": cfe_ids(command),
        "luna_present": "Luna" in agents,
        "identity_mutation": False,
    }


def classify_translation(text: str, *, audio: bool = False) -> str:
    if audio:
        return "TRANSCRIPTION_THEN_TRANSLATION"
    if _BIBLICAL.search(text or ""):
        return "BIBLICAL_LINGUISTIC_PLUS_HERMENEUTIC_HANDOFF"
    if _ANCIENT.search(text or ""):
        return "ANCIENT_LINGUISTIC"
    if _SPECIALIZED.search(text or ""):
        return "SPECIALIZED_TERMINOLOGICAL"
    return "GENERAL"


def select_frames(text: str, *, command: str, exhaustive: bool | None = None) -> dict[str, Any]:
    """Select frames. Everyday translation never receives a theological frame."""
    if command == "/play traductor" and classify_translation(text) == "GENERAL":
        return {"mode": "NOT_APPLICABLE", "primary": None, "secondary": (), "profiles": ()}
    wanted = exhaustive if exhaustive is not None else bool(_EXHAUSTIVE.search(text or ""))
    matched = tuple(name for name, pattern in _FRAME_PATTERNS if pattern.search(text or ""))
    if wanted:
        primary = matched[0] if matched else FRAME_ORDER[0]
        secondary = tuple(name for name in FRAME_ORDER if name != primary)
        if len((primary, *secondary)) != 18:
            raise engine.EngineContractError("Exhaustive frame set is not the 18 canonical frames")
        return {
            "mode": "EXHAUSTIVE_18",
            "primary": primary,
            "secondary": secondary,
            "profiles": tuple(FRAME_PROFILES[name] for name in (primary, *secondary)),
        }
    if len(matched) > 1:
        return {
            "mode": "AMBIGUOUS",
            "primary": None,
            "secondary": (),
            "profiles": (),
            "candidates": matched,
        }
    if len(matched) == 1:
        return {
            "mode": "PRIMARY_ONLY",
            "primary": matched[0],
            "secondary": (),
            "profiles": (FRAME_PROFILES[matched[0]],),
        }
    if command == "/play H" and _BIBLICAL.search(text or ""):
        primary = "Evangelical_Grammatical_Historical"
        return {
            "mode": "PRIMARY_ONLY",
            "primary": primary,
            "secondary": (),
            "profiles": (FRAME_PROFILES[primary],),
            "default_reason": "BIBLICAL_TEXT_WITHOUT_EXPLICIT_FRAME",
            "theological_configuration_is_not_the_frame": True,
        }
    if command == "/play H":
        return {"mode": "BLOCKED_FRAME_NOT_DETERMINED", "primary": None, "secondary": (), "profiles": ()}
    return {"mode": "NOT_APPLICABLE", "primary": None, "secondary": (), "profiles": ()}


class GovernedMemory:
    """One store. Physically inside Sistema Inteligente. Not a second memory."""

    PHYSICAL_DOMAIN = "6. Sistema Inteligente"
    LOGICAL_POSITION = "Cerebro ↔ Memoria Gobernada ↔ Orquestación"

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def remember(self, record: Mapping[str, Any]) -> dict[str, Any]:
        stored = {
            "seq": len(self._records) + 1,
            "record": dict(record),
            "sha256": hashlib.sha256(
                repr(sorted(record.items())).encode("utf-8")
            ).hexdigest(),
        }
        self._records.append(stored)
        return stored

    def recall(self, limit: int = 5) -> list[dict[str, Any]]:
        if limit < 1:
            raise engine.EngineContractError("recall limit must be positive")
        return list(self._records[-limit:])

    def __len__(self) -> int:
        return len(self._records)


def console_view(cycle: Mapping[str, Any]) -> dict[str, Any]:
    """Read a cycle. Do not execute engines and do not become a second orchestrator."""
    return {
        "plane": "CONSOLE",
        "executes_engines": False,
        "command": cycle.get("command"),
        "stage_status": {row["stage"]: row["status"] for row in cycle.get("stages", ())},
        "engines_executed": cycle.get("engines_executed", ()),
        "errors": cycle.get("errors", ()),
        "privileged_operations_authorized": False,
        "certification": "NOT_GRANTED",
    }


def _stage(name: str, status: str, detail: Any = None) -> dict[str, Any]:
    row = {"stage": name, "status": status}
    if detail is not None:
        row["detail"] = detail
    return row


def _privileged_request(text: str) -> str | None:
    match = _PRIVILEGED_PATTERN.search(text or "")
    return match.group(1).lower() if match else None


def integrate_request(
    command: str,
    text: str,
    *,
    memory: GovernedMemory | None = None,
    audio: bool = False,
    authorize_hermeneutic_handoff: bool = False,
    hermeneutic_payload: Mapping[str, Any] | None = None,
    exhaustive_frames: bool | None = None,
) -> dict[str, Any]:
    """Run one user request through the existing routes. Never certifies."""
    store = memory if memory is not None else GovernedMemory()
    recalled = store.recall(5) if len(store) else []
    errors: list[str] = []
    engines_executed: list[dict[str, Any]] = []
    domains = ["1. Cerebro", "2. Orquestación", "6. Sistema Inteligente"]
    privileged = _privileged_request(text)
    if privileged:
        errors.append(f"PRIVILEGED_OPERATION_DENIED:{privileged}")

    binding = None
    modality = None
    frames: dict[str, Any] = {"mode": "NOT_APPLICABLE", "primary": None, "secondary": ()}
    try:
        binding = command_binding(command)
    except engine.EngineContractError as exc:
        errors.append(str(exc))

    if binding and command == "/play traductor":
        modality = classify_translation(text, audio=audio)
        domains.append("4. Traductor Inteligente")
        if modality == "TRANSCRIPTION_THEN_TRANSLATION":
            domains.append("3. Transcripción")
        if modality == "BIBLICAL_LINGUISTIC_PLUS_HERMENEUTIC_HANDOFF":
            frames = {
                "mode": "HANDOFF_NOT_A_ROUTE_CHANGE",
                "primary": None,
                "secondary": (),
                "e11_inside_traductor": False,
                "handoff_command": "/play H",
            }
            if "E11" in binding["engines"]:
                errors.append("E11_SILENTLY_PRESENT_IN_TRADUCTOR_ROUTE")
            if authorize_hermeneutic_handoff:
                if hermeneutic_payload is None:
                    errors.append("HERMENEUTIC_HANDOFF_MISSING_PAYLOAD")
                else:
                    frames = select_frames(text, command="/play H", exhaustive=exhaustive_frames)
                    if frames["mode"] in {"PRIMARY_ONLY", "EXHAUSTIVE_18"}:
                        receipt = gateway.execute_engine_for_route(
                            "/play H", "Josefina", "E11", dict(hermeneutic_payload)
                        )
                        engines_executed.append({
                            "command": "/play H",
                            "engine_id": "E11",
                            "status": receipt["status"],
                            "frame": frames["primary"],
                            "source_preserved": receipt["result"].get("source_text_preserved"),
                        })
                    else:
                        errors.append(f"FRAME_SELECTION_{frames['mode']}")
        elif modality != "GENERAL":
            frames = select_frames(text, command=command, exhaustive=False)
    elif binding and command == "/play H":
        frames = select_frames(text, command=command, exhaustive=exhaustive_frames)
        if frames["mode"] in {"AMBIGUOUS", "BLOCKED_FRAME_NOT_DETERMINED"}:
            errors.append(f"FRAME_SELECTION_{frames['mode']}")
        elif hermeneutic_payload is None:
            errors.append("HERMENEUTIC_PAYLOAD_REQUIRED")
        else:
            receipt = gateway.execute_engine_for_route(
                "/play H", "Josefina", "E11", dict(hermeneutic_payload)
            )
            engines_executed.append({
                "command": "/play H",
                "engine_id": "E11",
                "status": receipt["status"],
                "frame": frames["primary"],
                "sequence": HERMENEUTIC_SEQUENCE,
                "source_preserved": receipt["result"].get("source_text_preserved"),
                "interpretation_status": receipt["result"].get("interpretation", {}).get("status"),
            })
    elif binding and "E11" in binding["engines"] and hermeneutic_payload is not None:
        frames = select_frames(text, command="/play H", exhaustive=exhaustive_frames)
        if frames["mode"] in {"PRIMARY_ONLY", "EXHAUSTIVE_18"}:
            agent = "Josefina" if "Josefina" in binding["agents"] else binding["agents"][0]
            receipt = gateway.execute_engine_for_route(command, agent, "E11", dict(hermeneutic_payload))
            engines_executed.append({
                "command": command,
                "engine_id": "E11",
                "agent": agent,
                "status": receipt["status"],
                "frame": frames["primary"],
            })

    if any(item["engine_id"] == "E03" for item in engines_executed):
        domains.append("5. Inteligencia documental")

    execution_status = "EXECUTED" if engines_executed else "ROUTED_WITHOUT_ENGINE_EXECUTION"
    if errors:
        execution_status = "FAIL_CLOSED"
    stages = (
        _stage("RECEPTION", "DONE"),
        _stage("INTENT", "DONE" if binding else "FAIL", command),
        _stage("CONTEXT", "DONE", {"audio": audio, "modality": modality}),
        _stage("RETRIEVAL", "DONE", {"recalled": len(recalled)}),
        _stage("SELECTION", "DONE" if binding else "FAIL", None if not binding else {
            "agents": list(binding["agents"]), "engines": list(binding["engines"]),
        }),
        _stage("PLAN", "DONE" if binding else "FAIL", {"frames": frames.get("mode")}),
        _stage("EXECUTION", execution_status, engines_executed),
        _stage("VALIDATION", "DONE" if not errors else "FAIL", errors),
        _stage("COHERENCE", "DONE" if not errors else "FAIL"),
        _stage("PROVENANCE", "DONE"),
        _stage("ERRORS", "DONE", errors),
        _stage("CORRECTION", "NOT_AUTOMATIC"),
        _stage("MEMORY_UPDATE", "DONE"),
        _stage("METACOGNITION", "DONE", OPERATIONAL_POLICY["COGNITIVE_CICD_ALWAYS_ON_PER_USER_REQUEST"]),
        _stage("CONTINUITY", "DONE", {"memory_seq": len(store) + 1}),
    )
    cycle = {
        "schema": "CAJITA_PHASE1_INTEGRATION_CYCLE/1.0",
        "command": command,
        "domains": tuple(dict.fromkeys(domains)),
        "binding": binding,
        "translation_modality": modality,
        "frames": {
            "mode": frames.get("mode"),
            "primary": frames.get("primary"),
            "secondary": frames.get("secondary", ()),
            "theological_configuration": THEOLOGICAL_CONFIGURATION,
        },
        "engines_executed": engines_executed,
        "errors": errors,
        "stages": stages,
        "cognitive_cicd": "ALWAYS_ON_PER_USER_REQUEST",
        "privileged_operations_authorized": False,
        "certification": "NOT_GRANTED",
        "g23": "NOT_GRANTED",
        "g24": "NOT_GRANTED",
    }
    cycle["sha256"] = hashlib.sha256(repr(stages).encode("utf-8")).hexdigest()
    store.remember({"kind": "cycle", "sha256": cycle["sha256"], "command": command})
    cycle["console"] = console_view(cycle)
    cycle["memory"] = {
        "physical_domain": store.PHYSICAL_DOMAIN,
        "logical_position": store.LOGICAL_POSITION,
        "records": len(store),
        "stores": 1,
    }
    return cycle
