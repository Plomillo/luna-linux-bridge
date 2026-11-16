#!/usr/bin/env python3
"""Expands only marginal frequencies to permit one-variable GUI descriptives.
Rows are frequency-expanded values; they are NOT linked respondent microdata.
"""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "datos" / "base_frecuencias_n39.csv"
out = root / "datos" / "base_expandida_marginal_n39.csv"
rows = list(csv.DictReader(source.open(encoding="utf-8-sig", newline="")))
by_q = {}
for row in rows:
    q = row.get("n_pregunta", "").strip()
    if not q:
        continue
    try:
        level = float(row["nivel"])
        frequency = int(row["frecuencia"])
        n = int(row["n"])
    except (ValueError, TypeError, KeyError):
        continue
    by_q.setdefault(q, []).append((row["pregunta"], level, row["etiqueta"], frequency, n))

expanded = []
audit = []
for q, items in sorted(by_q.items(), key=lambda x: int(x[0])):
    expected = {item[4] for item in items}
    if len(expected) != 1:
        raise SystemExit(f"N inconsistente en pregunta {q}: {expected}")
    n = expected.pop()
    total = sum(item[3] for item in items)
    if total != n or n != 39:
        raise SystemExit(f"Pregunta {q}: suma de frecuencias={total}, N={n}")
    question = items[0][0]
    for _label, level, response_label, frequency, _n in items:
        for _ in range(frequency):
            expanded.append({
                "pregunta_id": int(q),
                "pregunta": question,
                "respuesta_valor": int(level) if level.is_integer() else level,
                "respuesta_etiqueta": response_label,
            })
    audit.append({"pregunta_id": int(q), "n": total, "categorias": len(items)})

with out.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["pregunta_id","pregunta","respuesta_valor","respuesta_etiqueta"])
    writer.writeheader()
    writer.writerows(expanded)

manifest = {
    "source": source.name,
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "expanded_file": out.name,
    "expanded_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    "rows": len(expanded),
    "questions": audit,
    "interpretation": "Each question is a separate marginal distribution expanded to N=39 for univariate descriptive analysis. Rows across different questions are NOT the same respondents and must never be treated as paired or joint microdata.",
}
(root / "evidencia-gui").mkdir(exist_ok=True)
(root / "evidencia-gui" / "manifesto_datos.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(manifest, ensure_ascii=False, indent=2))
