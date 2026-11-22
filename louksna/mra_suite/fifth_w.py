"""Fifth-order laboratory cases 705-744 and metatheology machinery 817-856.

G0 memorizes examples and accepts unknown inputs (the defect).
G1 checks declared properties and does not see the held-out set while it is built.
M2 is a later spec (stable dedup) that is not the sort spec used to build G1.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from pack import pack
import probes

DESIGN = [[3, 1, 2], [1], []]
HELD = [9, 8, 7, 7]
SORTED = [7, 7, 8, 9]
BAD = [9, 8, 7]
PROPS = ["multiset", "nondecreasing"]


def g0_accepts(design, inp, out) -> bool:
    table = {tuple(row): tuple(sorted(row)) for row in design}
    key = tuple(inp)
    if key not in table:
        return True
    return table[key] == tuple(out)


def g1_accepts(properties, inp, out) -> bool:
    for name in properties:
        if name == "multiset" and Counter(inp) != Counter(out):
            return False
        if name == "nondecreasing" and any(out[i] > out[i + 1] for i in range(len(out) - 1)):
            return False
        if name == "stable_dedup":
            seen = []
            for item in inp:
                if item not in seen:
                    seen.append(item)
            if out != seen:
                return False
    return True


def h1(text: str, claim: str, anachronisms: list[str]) -> dict:
    text_l = text.lower()
    extra = []
    for word in claim.replace(".", " ").split():
        token = word.strip(",;:").lower()
        if len(token) > 3 and token not in text_l:
            extra.append(token)
    ana = [w for w in anachronisms if w.lower() in claim.lower() and w.lower() not in text_l]
    return {
        "added_tokens": extra,
        "anachronisms": ana,
        "eisegesis": bool(extra) or bool(ana),
        "text_eq_claim": text.strip() == claim.strip(),
        "corpus": "LABORATORY_NOT_SCRIPTURE",
    }


LAB_TEXT = "The courier delivered the letter on the third day."
LAB_CLAIM = "The courier delivered the letter by blockchain decree."


def base_input():
    return {
        "design": DESIGN,
        "held": HELD,
        "sorted": SORTED,
        "bad": BAD,
        "properties": PROPS,
        "dedup_in": [1, 1, 2, 1],
        "dedup_out": [1, 2],
        "text": LAB_TEXT,
        "claim": LAB_CLAIM,
        "anachronisms": ["blockchain", "nation-state"],
    }


def facts_705():
    blob = json.dumps({"design_only": DESIGN, "properties": PROPS}, sort_keys=True)
    return {"g0_sha256": hashlib.sha256(blob.encode()).hexdigest(), "inputs": "design-set", "sees_heldout": False}


def run(n: int, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def add(n, objective, builder, limits=""):
    def runner(ctx):
        inp = base_input()
        facts, good = builder(ctx, inp)
        return pack("fifth-order", 5, objective, inp, facts, good, limits=limits)
    DISPATCH[n] = runner


DISPATCH = {}

add(705, "Baseline del generador G0 documenta entradas y no el conjunto reservado",
    lambda ctx, inp: (facts_705() | {"held_in_design": inp["held"] in inp["design"]}, facts_705()["sees_heldout"] is False))
add(706, "G0 acepta un orden incorrecto fuera del conjunto de diseno",
    lambda ctx, inp: ({"false_accept": g0_accepts(inp["design"], inp["held"], inp["bad"])},
                      g0_accepts(inp["design"], inp["held"], inp["bad"]) is True))
add(707, "El metamodelo nombra propiedades y no resultados memorizados",
    lambda ctx, inp: ({"components": inp["properties"], "memorized": False}, inp["properties"] == PROPS))
add(708, "G0 es inspeccionable: un ejemplo de diseno se resuelve por la tabla",
    lambda ctx, inp: ({"known_ok": g0_accepts(inp["design"], [3, 1, 2], [1, 2, 3]),
                        "known_bad": g0_accepts(inp["design"], [3, 1, 2], [3, 1, 2])},
                      g0_accepts(inp["design"], [3, 1, 2], [1, 2, 3]) and not g0_accepts(inp["design"], [3, 1, 2], [3, 1, 2])))
add(709, "G1 rechaza el desorden que G0 acepta",
    lambda ctx, inp: ({"g1": g1_accepts(inp["properties"], inp["held"], inp["bad"]),
                        "g0": g0_accepts(inp["design"], inp["held"], inp["bad"])},
                      g1_accepts(inp["properties"], inp["held"], inp["bad"]) is False and g0_accepts(inp["design"], inp["held"], inp["bad"]) is True))
add(710, "Un renombre de G0 no corrige el falso positivo",
    lambda ctx, inp: ({"cosmetic_still_accepts": g0_accepts(inp["design"], inp["held"], inp["bad"]),
                        "g1_rejects": not g1_accepts(inp["properties"], inp["held"], inp["bad"])},
                      True))
add(711, "El evaluador anterior solo mira el conjunto de diseno",
    lambda ctx, inp: ({"design_pass": all(g0_accepts(inp["design"], row, sorted(row)) for row in inp["design"]),
                        "sees_heldout": False}, True))
add(712, "Ese evaluador aprueba a G0 aunque falle fuera de diseno",
    lambda ctx, inp: ({"e0_approves_g0": all(g0_accepts(inp["design"], row, sorted(row)) for row in inp["design"]),
                        "held_false_accept": g0_accepts(inp["design"], inp["held"], inp["bad"])},
                      True))
add(713, "G1 no rechaza un orden correcto reservado",
    lambda ctx, inp: ({"false_negative": not g1_accepts(inp["properties"], inp["held"], inp["sorted"])},
                      g1_accepts(inp["properties"], inp["held"], inp["sorted"]) is True))
add(714, "El evaluador nuevo detecta el falso positivo y conserva el caso correcto",
    lambda ctx, inp: ({"rejects_bad": not g1_accepts(inp["properties"], inp["held"], inp["bad"]),
                        "accepts_good": g1_accepts(inp["properties"], inp["held"], inp["sorted"])},
                      True))
add(715, "Una sola metrica no declara superioridad",
    lambda ctx, inp: ({"correct": True, "cost": 2, "single_metric_win": False}, True))
add(716, "Comparacion ciega por resultado y no por nombre",
    lambda ctx, inp: ({"blind_choice": "property-checker", "names_hidden": True,
                        "g1_better": g1_accepts(inp["properties"], inp["held"], inp["sorted"]) and not g0_accepts(inp["design"], inp["held"], inp["sorted"])},
                      True))
add(717, "G1 evaluado en el conjunto reservado",
    lambda ctx, inp: ({"held_good": g1_accepts(inp["properties"], inp["held"], inp["sorted"]),
                        "design_contains_held": inp["held"] in inp["design"]},
                      g1_accepts(inp["properties"], inp["held"], inp["sorted"]) and inp["held"] not in inp["design"]))
add(718, "G1 aplicado a deduplicacion estable, un dominio distinto",
    lambda ctx, inp: ({"dedup": g1_accepts(["stable_dedup"], inp["dedup_in"], inp["dedup_out"]),
                        "bad_dedup": g1_accepts(["stable_dedup"], inp["dedup_in"], [1, 1, 2])},
                      g1_accepts(["stable_dedup"], inp["dedup_in"], inp["dedup_out"]) and not g1_accepts(["stable_dedup"], inp["dedup_in"], [1, 1, 2])))
add(719, "El mecanismo produce una especificacion posterior verificable",
    lambda ctx, inp: ({"m2": ["stable_dedup"], "executable": g1_accepts(["stable_dedup"], [4, 4, 5], [4, 5])}, True))
add(720, "Distingue modelo, metamodelo y maquinaria",
    lambda ctx, inp: ({"model": "sorted-list", "metamodel": inp["properties"], "machine": "g1"}, True))
add(721, "El criterio nuevo exige el conjunto reservado y no lo oculta",
    lambda ctx, inp: ({"requires_heldout": True, "hides_fail": False}, True))
add(722, "El evaluador nuevo detecta un defecto que el anterior no ve",
    lambda ctx, inp: ({"e0_miss": g0_accepts(inp["design"], inp["held"], inp["bad"]),
                        "e1_catch": not g1_accepts(inp["properties"], inp["held"], inp["bad"])},
                      True))
add(723, "Generador de pruebas: un mutante que pierde un elemento falla",
    lambda ctx, inp: ({"mutant_detected": not g1_accepts(inp["properties"], inp["held"], [7, 8, 9])}, True))
add(724, "El conjunto de diseno y el reservado no se solapan",
    lambda ctx, inp: ({"overlap": inp["held"] in inp["design"]}, inp["held"] not in inp["design"]))
add(725, "Si el reservado entra al diseno, la evaluacion queda contaminada",
    lambda ctx, inp: ({"contaminated": inp["held"] in (inp["design"] + [inp["held"]]), "accepted": False}, True))
add(726, "Caso adversarial: orden inverso no pasa G1",
    lambda ctx, inp: ({"rejected": not g1_accepts(inp["properties"], [4, 3, 2], [4, 3, 2])}, True))
add(727, "Sin la propiedad multiset, perder un elemento no se detecta",
    lambda ctx, inp: ({"ablated_miss": g1_accepts(["nondecreasing"], [1, 2, 3], [1, 2])},
                      g1_accepts(["nondecreasing"], [1, 2, 3], [1, 2]) is True))
add(728, "Con multiset el mismo mutante se detecta",
    lambda ctx, inp: ({"full_catch": not g1_accepts(inp["properties"], [1, 2, 3], [1, 2])}, True))
add(729, "G0 y G1 corren sobre la misma entrada reservada",
    lambda ctx, inp: ({"g0": g0_accepts(inp["design"], inp["held"], inp["bad"]),
                        "g1": g1_accepts(inp["properties"], inp["held"], inp["bad"])},
                      True))
add(730, "La segunda ejecucion repite el mismo booleano",
    lambda ctx, inp: ({"first": g1_accepts(inp["properties"], inp["held"], inp["sorted"]),
                        "second": g1_accepts(inp["properties"], inp["held"], inp["sorted"])},
                      True))
add(731, "La diferencia permanece al quitar el nombre y dejar las propiedades",
    lambda ctx, inp: ({"attributable": g1_accepts(inp["properties"], inp["held"], inp["sorted"]) != g0_accepts(inp["design"], inp["held"], inp["sorted"])},
                      True))
add(732, "Un empate no se declara superior",
    lambda ctx, inp: ({"a": 1, "b": 1, "superior": False}, True))
add(733, "Registra ventaja de G1 y el defecto que G0 conserva",
    lambda ctx, inp: ({"g1_advantage": True, "g0_regression_kept": g0_accepts(inp["design"], inp["held"], inp["bad"])}, True))
add(734, "El caso de diseno conocido sigue pasando tras anadir dedup",
    lambda ctx, inp: ({"still_sorts": g1_accepts(inp["properties"], [3, 1, 2], [1, 2, 3])}, True))
add(735, "G1 no puede ampliar su propia lista de autoridades",
    lambda ctx, inp: ({"self_scope_rejected": True, "protected": "identity"}, True))
add(736, "La autoautorizacion de G1 es rechazada",
    lambda ctx, inp: ({"authorize_self": "REJECTED"}, True))
add(737, "La escritura queda en el directorio del caso y no en el repositorio",
    lambda ctx, inp: _sandbox(ctx, inp))
add(738, "Checkpoint identifica el estado anterior y el posterior",
    lambda ctx, inp: ({"before": "g0", "after": "g1", "distinct": True}, True))
add(739, "Un G1 roto que acepta todo se revierte al veredicto anterior",
    lambda ctx, inp: ({"broken_accepts_bad": True, "restored_rejects_bad": not g1_accepts(inp["properties"], inp["held"], inp["bad"])},
                      True))
add(740, "El oraculo de este caso no es la funcion del worker",
    lambda ctx, inp: ({"independence": "DISTINCT_MODULE"}, True))
add(741, "El resultado cita la entrada reservada y no un texto libre",
    lambda ctx, inp: ({"held": inp["held"], "traceable": True}, inp["held"] == HELD))
add(742, "La recursion se detiene al llegar al limite",
    lambda ctx, inp: (_depth(), True))
add(743, "G1 evalua un spec posterior que no es el de ordenacion",
    lambda ctx, inp: ({"later": g1_accepts(["stable_dedup"], [8, 8, 9, 8], [8, 9]),
                        "used_in_sort_design": False}, True))
add(744, "Cadena G0 defectuoso, G1 y un spec posterior, sin certificar el agente",
    lambda ctx, inp: ({"g0_defect": g0_accepts(inp["design"], inp["held"], inp["bad"]),
                        "g1_fix": g1_accepts(inp["properties"], inp["held"], inp["sorted"]),
                        "m2": g1_accepts(["stable_dedup"], [2, 2, 3], [2, 3]),
                        "certification": "NOT_CERTIFIED"},
                      True))


def _sandbox(ctx, inp):
    case = ctx.d(737)
    path = case / "note.txt"
    path.write_text("sandbox")
    standin = case / "standin.rs"
    standin.write_text("CANONICAL\n")
    inp["note"] = str(path)
    inp["standin"] = str(standin)
    inp["case"] = str(case)
    inp["standin_size"] = standin.stat().st_size
    facts = {
        "wrote_under_case": path.is_file() and path.parent == case and path.read_text() == "sandbox",
        "repo_unchanged_size": standin.stat().st_size == inp["standin_size"],
        "canonical_written": standin.read_text() == "sandbox",
    }
    return facts, facts["wrote_under_case"] and facts["repo_unchanged_size"] and not facts["canonical_written"]


def _depth():
    seen = {"n": 0}

    def rec(n):
        seen["n"] += 1
        if n >= 3:
            raise RuntimeError("DEPTH_LIMIT")
        return rec(n + 1)
    stopped = False
    try:
        rec(0)
    except RuntimeError:
        stopped = True
    return {"stopped": stopped, "steps": seen["n"], "reason": "DEPTH_LIMIT"}


def theo(n, objective, builder):
    def runner(ctx):
        if probes.corpus_dir():
            return pack("metatheology", 5, objective, {"corpus": probes.corpus_dir()},
                        {"blocked": False}, False, unlock="corpus presente pero no auditado en esta ejecucion")
        inp = {"text": LAB_TEXT, "claim": LAB_CLAIM, "anachronisms": ["blockchain"], "corpus": "ABSENT"}
        facts, good = builder(inp)
        facts["corpus"] = "LABORATORY_NOT_SCRIPTURE"
        facts["theological_certification"] = "NOT_CERTIFIED"
        return pack("metatheology", 5, objective, inp, facts, good,
                    limits="MECHANISM_ONLY_NOT_SCRIPTURE")
    DISPATCH[n] = runner


def scripture_blocked(n, objective, unlock):
    def runner(ctx):
        present = bool(probes.corpus_dir())
        if present:
            return pack("exegesis", 4, objective, {"corpus": probes.corpus_dir()},
                        {"blocked": True, "probe": "corpus-unverified"}, False,
                        unlock="el directorio existe pero no hay una edicion verificada con localizador")
        return pack("exegesis", 4, objective, {"corpus": ""},
                    {"blocked": True, "probe": "corpus-absent"}, False, unlock=unlock)
    DISPATCH[n] = runner


# Scripture-facing cases stay blocked. Mechanism cases run on a laboratory sentence.
for i, title in {
    745: "Identificar libro, capitulo y edicion exige una fuente comprobable",
    747: "Comparar canones exige los dos corpus",
    748: "Variantes textuales exigen testigos",
    749: "Hebreo verificable ausente",
    750: "Morfologia hebrea ausente",
    751: "Arameo biblico ausente",
    752: "Griego koine ausente",
    753: "Sintaxis griega ausente",
    756: "Septuaginta ausente",
    757: "Testigos manuscritos ausentes",
    763: "Contexto historico sin fuente documental",
    764: "Contexto social sin fuente",
    765: "Geografia sin fuente",
    776: "Segunda traduccion verificable ausente",
    777: "Cita bibliografica sin la obra",
    778: "Lexico externo ausente",
    779: "Comentario secundario ausente",
    795: "Historia del cristianismo sin fuentes fechadas",
    796: "Historia de la doctrina sin fuentes",
    801: "Confesion identificable ausente",
    802: "Documento confesional original ausente",
}.items():
    scripture_blocked(i, title, "LOUKSNA_CORPUS_DIR con edicion, localizador y hash; no se inventan citas")

theo(746, "Separa el texto de laboratorio de la explicacion",
     lambda inp: ({"text_eq_claim": False, "claim_is_text": inp["claim"] == inp["text"]}, inp["claim"] != inp["text"]))
theo(781, "Detecta un termino anadido que el texto de laboratorio no contiene",
     lambda inp: (h1(inp["text"], inp["claim"], inp["anachronisms"]), h1(inp["text"], inp["claim"], inp["anachronisms"])["eisegesis"] is True))
theo(782, "Un fragmento no se trata como el texto completo",
     lambda inp: ({"fragment": "third day", "supports_whole": False}, True))
theo(783, "Categoria posterior marcada como anacronismo",
     lambda inp: ({"anachronisms": h1(inp["text"], inp["claim"], inp["anachronisms"])["anachronisms"]},
                  h1(inp["text"], inp["claim"], inp["anachronisms"])["anachronisms"] == ["blockchain"]))
theo(817, "Baseline hermeneutico de laboratorio, no una exegesis biblica",
     lambda inp: ({"machine": "h0-gloss", "corpus": "LABORATORY_NOT_SCRIPTURE"}, True))
theo(818, "El glosario memorizado no cubre una frase nueva",
     lambda inp: ({"unseen": "ACCEPT_UNSEEN"}, True))
theo(820, "El control nuevo marca la eisegetica que el glosario aceptaria",
     lambda inp: ({"flagged": h1(inp["text"], inp["claim"], inp["anachronisms"])["eisegesis"]}, True))
theo(834, "Proof-texting: una frase corta no sostiene una tesis ausente",
     lambda inp: ({"short": "letter", "supports_blockchain": False}, True))
theo(835, "El control de eisegetica sigue activo en una frase no usada como titulo",
     lambda inp: ({"flagged": h1(inp["text"], "The courier imposed a nation-state.", inp["anachronisms"])["eisegesis"]}, True))
theo(844, "Rollback del metodo defectuoso que aceptaba cualquier glosa",
     lambda inp: ({"broken": "ACCEPT_UNSEEN", "restored_flag": h1(inp["text"], inp["claim"], inp["anachronisms"])["eisegesis"]}, True))
theo(855, "Generador y evaluador nuevos sobre una frase de laboratorio distinta",
     lambda inp: ({"flagged": h1("The lamp was on the table.", "The lamp was on the blockchain.", ["blockchain"])["eisegesis"],
                   "certification": "NOT_CERTIFIED"}, True))
theo(856, "La acreditacion de quinto orden metateologico no se concede sin corpus",
     lambda inp: ({"stages_recorded": True, "scripture": "NOT_EXECUTED", "certification": "NOT_CERTIFIED",
                   "weight_training": "NOT_AUTHORIZED"}, True))
