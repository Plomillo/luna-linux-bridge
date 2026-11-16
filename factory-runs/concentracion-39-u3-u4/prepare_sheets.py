#!/usr/bin/env python3
from __future__ import annotations
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SOURCE = DATA / "base_frecuencias_n39.csv"
STATS = {
    "R 4.5.3": DATA / "descriptivos_R_4_5_3.csv",
    "jamovi / jmv 2.8.0": DATA / "descriptivos_jamovi_jmv.csv",
    "JASP / jaspDescriptives 0.96.5": DATA / "descriptivos_jasp.csv",
}
ledger = json.loads((ROOT / "profiles" / "source-ledger.json").read_text(encoding="utf-8"))
raw = list(csv.DictReader(SOURCE.open(encoding="utf-8-sig", newline="")))
response_rows = [r for r in raw if r.get("tipo") in {"RESPUESTA", "RESPUESTA_EDAD"}]
by_question = {}
for row in response_rows:
    by_question.setdefault(int(row["n_pregunta"]), []).append(row)
if sorted(by_question) != [1, 2, 3, 4, 5, 6]:
    raise SystemExit("QUESTION_SET_INVALID")
quality = [["Control", "Estado", "Evidencia"]]
for q, rows in sorted(by_question.items()):
    totals = {int(r["n"]) for r in rows}
    observed = sum(int(r["frecuencia"]) for r in rows)
    if totals != {39} or observed != 39:
        raise SystemExit(f"FREQUENCY_TOTAL_FAIL_Q{q}:{observed}:{totals}")
    quality.append([f"Pregunta {q}", "PASS", f"{observed} categorías observadas; N=39; suma verificada"])
freq = [["ID pregunta", "Pregunta", "Valor", "Categoría", "Frecuencia", "N", "Porcentaje (%)"]]
for q, rows in sorted(by_question.items()):
    for r in rows:
        n, count = int(r["n"]), int(r["frecuencia"])
        freq.append([q, r["pregunta"], r["nivel"], r["etiqueta"], count, n, round(100*count/n, 1)])
summary = [["Motor", "Pregunta", "N", "Media", "Mediana", "Moda", "DE", "Mínimo", "Máximo"]]
for engine, path in STATS.items():
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            summary.append([
                engine, row.get("pregunta", f"P{row.get('n_pregunta','')}"), int(row["n"]),
                float(row["media"]), float(row["mediana"]), row.get("moda", ""),
                float(row["de"]), float(row["minimo"]), float(row["maximo"])
            ])
dictionary = [
 ["Variable", "Definición", "Tipo", "Codificación", "Sentido de puntuaciones altas"],
 ["Edad", "Edad declarada", "Cuantitativa", "Años", "Mayor edad"],
 ["Planificación previa", "Pensó qué haría primero antes de estudiar", "Ordinal", "1 Nunca; 2 Casi nunca; 3 Algunas veces; 4 Casi siempre; 5 Siempre", "Mayor frecuencia de planificación"],
 ["Continuidad ante distractores", "Pudo seguir haciendo la tarea aunque algo llamara su atención", "Ordinal", "1 Nunca; 2 Casi nunca; 3 Algunas veces; 4 Casi siempre; 5 Siempre", "Mayor continuidad declarada"],
 ["Dificultad del objeto", "Dificultad para mantener la mirada en un objeto durante cinco minutos", "Ordinal", "1 No me costó nada; 5 Me costó mucho", "Mayor dificultad percibida"],
 ["Dificultad del poema", "Dificultad para comprender el poema", "Ordinal", "1 No me costó nada; 5 Me costó mucho", "Mayor dificultad percibida"],
 ["Esfuerzo", "Esfuerzo declarado para completar la prueba", "Valoración 0–10", "0 Ningún esfuerzo; 10 Muchísimo esfuerzo", "Mayor esfuerzo subjetivo"]
]
contrasts = [
 ["Hipótesis", "Expectativa", "Datos observados", "Evaluación"],
 ["H1 Planificación", "Predominio de siempre/casi siempre", "30/39 = 76,9 %", "Respaldada descriptivamente"],
 ["H2 Continuidad", "Predominio de siempre/casi siempre", "22/39 = 56,4 %", "Respaldada parcialmente"],
 ["H3 Objeto", "Una parte declararía dificultad", "51,3 % nula/leve; 48,7 % alguna dificultad", "Resultado mixto; práctica no medida"],
 ["H4 Poema", "La familiaridad lectora podría acompañar menor dificultad", "79,5 % nula/leve", "No respalda dificultad generalizada; hábito no medido"],
 ["H5 Esfuerzo", "Predominio de esfuerzo bajo/moderado", "66,7 % entre 0 y 4; 33,3 % entre 5 y 10", "Respaldada parcialmente"]
]
qc = quality + [
 ["Respuestas enlazadas por participante", "NO DISPONIBLE", "La exportación solo contiene frecuencias marginales"],
 ["Correlaciones entre preguntas", "NO EJECUTABLE", "No existen identificadores individuales enlazados"],
 ["Datos sintéticos", "PROHIBIDOS", "No se generaron registros individuales"],
 ["Expansión para interfaz", "SOLO UNIVARIADA", "39 valores derivados por pregunta; no emparejar preguntas"]
]
sheets = [
 {"name":"Frecuencias","rows":freq},
 {"name":"Descriptivos_tres_motores","rows":summary},
 {"name":"Diccionario","rows":dictionary},
 {"name":"Contraste_H1_H5","rows":contrasts},
 {"name":"Control_calidad","rows":qc}
]
for name in ("entrega3-base","entrega3-informe","entrega4-resultados","entrega4-informe"):
    d = ROOT / "workspaces" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    (d / "sheets.json").write_text(json.dumps({"sheets":sheets}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (d / "source-ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print("DATA_VALIDATION=PASS; QUESTIONS=6; N_PER_QUESTION=39; WORKSPACES=4")
