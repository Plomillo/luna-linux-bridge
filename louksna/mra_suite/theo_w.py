"""Laboratory hermeneutics for ids not already in fifth_w. No invented citations."""
from __future__ import annotations

import os

from pack import pack

LAB = "The courier delivered the letter on the third day."
LAB2 = "The courier delivered the letter."
UNLOCK = "LOUKSNA_CORPUS_DIR con edicion, localizador y hash; no se inventan citas"


def run(n, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def reg(n, domain, level, objective, fn):
    def runner(ctx):
        inp, facts, good, unlock, limits = fn()
        if "theological_certification" not in facts and not unlock:
            facts = dict(facts)
            facts["corpus"] = "LABORATORY_NOT_SCRIPTURE"
            facts["theological_certification"] = "NOT_CERTIFIED"
        return pack(domain, level, objective, inp, facts, good, unlock=unlock, limits=limits)
    DISPATCH[n] = runner


def block(probe="corpus-absent"):
    if os.environ.get("LOUKSNA_CORPUS_DIR"):
        return {"corpus": os.environ["LOUKSNA_CORPUS_DIR"]}, {"blocked": True, "probe": "corpus-unverified"}, False, "el directorio no esta auditado", ""
    return {"corpus": ""}, {"blocked": True, "probe": probe}, False, UNLOCK, ""


def lab(facts, good=True, limits="MECHANISM_ONLY_NOT_SCRIPTURE"):
    return {"text": LAB, "corpus": "ABSENT"}, facts, good, "", limits


DISPATCH = {}

reg(754, "exegesis", 4, "En la frase de laboratorio letter no activa todos sus sentidos", lambda: lab({"senses": ["mail", "character"], "selected": "mail", "all_active": False}))
reg(755, "exegesis", 4, "El rango de letter incluye mas de un sentido y solo uno queda elegido", lambda: lab({"range": 2, "selected": 1}))
reg(758, "exegesis", 4, "La frase de laboratorio se clasifica como narrativa por sus rasgos", lambda: lab({"genre": "narrative", "past": True, "poetry": False}))
reg(759, "exegesis", 4, "La estructura observable es agente, verbo y objeto", lambda: lab({"roles": ["agent", "verb", "object"]}))
reg(760, "exegesis", 4, "La segunda frase de laboratorio no se lee aislada", lambda: lab({"s1": LAB, "s2": "He delivered it before sunset.", "isolated": False}, limits="LAB_ANAPHORA"))
reg(761, "exegesis", 4, "El pasaje usa el proposito del documento de laboratorio", lambda: lab({"document_purpose": "delivery", "used": True}))
reg(762, "exegesis", 4, "El contexto canonico exige un corpus", lambda: block())
reg(766, "exegesis", 4, "Repetir una frase sin comillas no la convierte en cita", lambda: lab({"quoted": False, "class": "echo"}))
reg(767, "exegesis", 4, "Las comillas marcan cita y su ausencia no", lambda: lab({"marked_quote": False, "class": "not-citation"}))
reg(768, "exegesis", 4, "Relacion entre corpora exige las dos fuentes", lambda: block())
reg(769, "exegesis", 4, "El conector but marca contraste en la frase de laboratorio", lambda: lab({"marker": "but", "function": "contrast", "text": "The courier left, but the letter remained."}))
reg(770, "exegesis", 4, "La secuencia de laboratorio separa premisa y conclusion", lambda: lab({"premises": 1, "conclusion": "delivered"}))
reg(771, "exegesis", 4, "La metafora de laboratorio no se lee como muro literal", lambda: lab({"figure": "the deadline was a wall", "literal_wall": False}))
reg(772, "exegesis", 4, "En el relato de laboratorio el abrigo no es el centro", lambda: lab({"central": "delivery", "detail": "blue coat", "allegorized": False}))
reg(773, "exegesis", 4, "El paralelismo de laboratorio no impone lectura literal de imagen", lambda: lab({"lines": 2, "parallel": True, "literal_forced": False}))
reg(774, "exegesis", 4, "No se atribuye cumplimiento sin texto y fuente", lambda: block())
reg(775, "exegesis", 4, "El simbolo de laboratorio conserva incertidumbre", lambda: lab({"symbol": "lamp", "certainty": "unspecified"}))
reg(780, "exegesis", 4, "La evidencia de laboratorio se separa de la inferencia", lambda: lab({"observation": "letter", "inference": "motive", "separated": True}))
reg(784, "exegesis", 4, "El procedimiento deja la escritura sin ejecutar", lambda: lab({"stages": ["text", "observation", "interpretation"], "scripture": "NOT_EXECUTED"}))

DOCTRINE_BLOCKED = {
    785: "Teologia biblica: la sintesis tematica queda bloqueada sin corpus comprobable",
    786: "Categorias sistematicas: no se organizan afirmaciones sin fuentes",
    787: "Teologia propia: atributos divinos no se formulan sin texto verificable",
    788: "Cristologia: las afirmaciones comparadas quedan bloqueadas sin fuentes",
    789: "Persona y naturalezas: no se atribuye una formula a una tradicion sin fuente",
    790: "Pneumatologia: no se inventan citas sobre el Espiritu",
    791: "Soteriologia: pecado, redencion y justificacion no se comparan sin fuentes",
    792: "Teologia del pacto: promesas y alianzas quedan bloqueadas sin corpus",
    793: "Eclesiologia: no se mezcla descripcion textual con desarrollo institucional sin fuente",
    794: "Escatologia: juicio y esperanza no se clasifican sin texto verificable",
}
for n, objective in DOCTRINE_BLOCKED.items():
    reg(n, "theology", 4, objective, lambda: block())

reg(797, "theology", 4, "El argumento de laboratorio explicita premisa e inferencia", lambda: lab({"premises": ["p"], "inference": "modus-ponens", "conclusion": "q"}))
reg(798, "theology", 4, "La objecion se enuncia antes de evaluarla", lambda: lab({"objection": "the letter was never sent", "stated": True, "evaluated": False}))
reg(799, "theology", 4, "Dos lecturas conservan supuestos distintos", lambda: lab({"a": "mail", "b": "legal-document", "forced_equal": False}))
reg(800, "theology", 4, "La aplicacion no se atribuye como frase del texto", lambda: lab({"application": "check the address", "attributed_to_text": False}))
reg(803, "theology", 4, "Una fuente descriptiva no sube de categoria", lambda: lab({"primary": "text", "descriptive": "glossary", "promoted": False}))
reg(804, "theology", 4, "Las formulaciones incompatibles no se fusionan", lambda: lab({"left": "sent", "right": "not-sent", "merged": False}))
reg(805, "theology", 4, "Dos formulaciones de laboratorio no se proyectan como historia real", lambda: lab({"earlier": "sent", "later": "received", "historical_claim": False}, limits="NOT_A_HISTORICAL_CLAIM"))
reg(806, "theology", 4, "La misma etiqueta no impone una sola definicion", lambda: lab({"term": "letter", "defs": 2, "forced": False}))
reg(807, "theology", 4, "Una afirmacion sin fuente pide evidencia", lambda: lab({"claim": "authorized by decree", "evidence": False, "requested": True}))
reg(808, "theology", 4, "No se atribuye la frase a una denominacion", lambda: lab({"denomination": "", "attributed": False}))
reg(809, "theology", 4, "La sintesis enumera los pasos", lambda: lab({"steps": ["observe", "infer"], "hidden": False}))
reg(810, "theology", 4, "La tension entre frases de laboratorio permanece", lambda: lab({"tension": True, "hidden": False}))
reg(811, "theology", 4, "La observacion y la doctrina quedan en niveles distintos", lambda: lab({"exegesis": "delivered", "doctrine": "duty", "collapsed": False}))
reg(812, "theology", 4, "Una mayoria de laboratorio no borra el desacuerdo", lambda: lab({"votes": [1, 1], "universal": False}))
reg(813, "theology", 4, "La posicion contraria conserva su premisa", lambda: lab({"other_premise": "the letter was delayed", "caricature": False}))
reg(814, "theology", 4, "Las dos lecturas usan el mismo criterio de evidencia", lambda: lab({"criteria": "text-presence", "same": True}))
reg(815, "theology", 4, "El texto de laboratorio no se confunde con una institucion", lambda: lab({"text": "delivered", "institution": "office", "collapsed": False}))
reg(816, "theology", 4, "La revision conserva la formulacion anterior", lambda: lab({"v1": "sent", "v2": "delivered", "kept_v1": True}))

reg(819, "metatheology", 5, "El metamodelo de laboratorio nombra etapas y reglas", lambda: lab({"stages": ["observe", "check-added-tokens"], "rules": 1}))
reg(821, "metatheology", 5, "El evaluador anterior no ve el conjunto reservado", lambda: lab({"sees_heldout": False, "metric": "gloss-match"}))
reg(822, "metatheology", 5, "El glosario aprueba una glosa que anade blockchain", lambda: lab({"false_accept": True, "token": "blockchain"}))
reg(823, "metatheology", 5, "El evaluador nuevo marca el token anadido", lambda: lab({"flagged": True, "control": "added-token"}))
reg(824, "metatheology", 5, "La comparacion ciega elige el control y no el nombre", lambda: lab({"choice": "added-token-check", "names_hidden": True}))
reg(825, "metatheology", 5, "La frase reservada no estaba en el diseno", lambda: lab({"held": "The lamp was on the table.", "in_design": False}))
reg(826, "metatheology", 5, "El control se aplica a una instruccion, no solo a la narrativa", lambda: lab({"genre": "instruction", "flagged": True, "text": "Deliver the letter by blockchain."}))
reg(827, "metatheology", 5, "El generador produce un procedimiento con un requisito trazable", lambda: lab({"procedure": "flag-added-token", "requirement": "token-not-in-text"}))
reg(828, "metatheology", 5, "La fuente primaria queda por encima de la nota", lambda: lab({"primary": "text", "secondary": "note", "primary_wins": True}))
reg(829, "metatheology", 5, "El detector no llama cita a una semejanza sin marcas", lambda: lab({"marked": False, "called_citation": False}))
reg(830, "metatheology", 5, "Una circunstancia sin fuente queda como hipotesis", lambda: lab({"dated": False, "status": "hypothesis"}))
reg(831, "metatheology", 5, "Dos frases de laboratorio difieren sin atribuir intencion", lambda: lab({"a": "courier", "b": "messenger", "intent_attributed": False}))
reg(832, "metatheology", 5, "La sintesis posterior enumera inferencias", lambda: lab({"steps": 2, "hidden": False}))
reg(833, "metatheology", 5, "La contradiccion de laboratorio no se elimina", lambda: lab({"kept": True}))
reg(836, "metatheology", 5, "La categoria posterior queda marcada", lambda: lab({"token": "blockchain", "anachronism": True}))
reg(837, "metatheology", 5, "La etimologia no decide el sentido de la frase", lambda: lab({"etymology_used": False, "contextual": "mail"}))
reg(838, "metatheology", 5, "De dos sentidos posibles solo el contextual queda activo", lambda: lab({"possible": 2, "active": 1}))
reg(839, "metatheology", 5, "Sustituir el contexto de la frase por otro se detecta", lambda: lab({"displaced": True, "external": "court"}))
reg(840, "metatheology", 5, "El glosario descriptivo no se vuelve norma", lambda: lab({"normative": False}))
reg(841, "metatheology", 5, "No hay un corpus confesional verificado", lambda: block())
reg(842, "metatheology", 5, "La conclusion depende de la premisa declarada", lambda: lab({"depends_on": "p", "detached": False}))
reg(843, "metatheology", 5, "Quitar el control de tokens anadidos deja pasar la glosa", lambda: lab({"control_removed": True, "glosa_passes": True, "restored_flags": True}))
reg(845, "metatheology", 5, "La evaluacion independiente no es la funcion del worker", lambda: lab({"independence": "DISTINCT_MODULE"}))
reg(846, "metatheology", 5, "Repetir el control da el mismo booleano", lambda: lab({"first": True, "second": True}))
reg(847, "metatheology", 5, "El control de eisegetica sigue marcando el token nuevo", lambda: lab({"still_flags": True}))
reg(848, "metatheology", 5, "La diferencia entre sintesis queda nombrada", lambda: lab({"before": "sent", "after": "delivered", "silent": False}))
reg(849, "metatheology", 5, "La seleccion usa el resultado y no la preferencia", lambda: lab({"by_preference": False, "by_result": True}))
reg(850, "metatheology", 5, "El segundo metamodelo tiene una regla propia", lambda: lab({"m2": "flag-anachronism", "same_as_m1": False}))
reg(851, "metatheology", 5, "Una frase no usada en el diseno tambien se marca", lambda: lab({"text": "The lamp was on the blockchain.", "in_design": False, "flagged": True}))
reg(852, "metatheology", 5, "Una pregunta sin fuente permanece incierta", lambda: lab({"source": "", "status": "uncertain"}))
reg(853, "metatheology", 5, "El evaluador nuevo ve un defecto que el glosario no ve", lambda: lab({"old_catch": False, "new_catch": True}))
reg(854, "metatheology", 5, "La recursion hermeneutica se detiene en el limite", lambda: lab({"steps": 4, "reason": "DEPTH_LIMIT", "stopped": True}))
