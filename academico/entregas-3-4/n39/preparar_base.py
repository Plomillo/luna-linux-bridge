#!/usr/bin/env python3
"""Organiza la base a partir del CSV oficial, línea por línea. No inventa filas."""
import csv
import hashlib
import json
from pathlib import Path

SRC = Path("/workspace/attachments/encuesta_atencion_resultados_39_respuestas_integral.csv")
OUT = Path("/workspace/lunita-n39")
DATOS = OUT / "datos"
DATOS.mkdir(parents=True, exist_ok=True)

raw = SRC.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
text = raw.decode("utf-8-sig")
rows = list(csv.DictReader(text.splitlines()))
if not rows:
    raise SystemExit("CSV vacío")

# copia íntegra, mismos bytes
dest = DATOS / SRC.name
dest.write_bytes(raw)

cols = list(rows[0].keys())
line_out = DATOS / "base_linea_por_linea.csv"
with line_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["linea_archivo", *cols])
    w.writeheader()
    for i, row in enumerate(rows, start=2):
        w.writerow({"linea_archivo": i, **row})

# frecuencias: solo filas de respuesta, nunca totales ni títulos
freq_rows = []
for i, row in enumerate(rows, start=2):
    tipo = row["Tipo de fila"]
    if tipo not in ("RESPUESTA_EDAD", "RESPUESTA"):
        continue
    rec = (row["Recuento"] or "").strip()
    if rec == "" or not rec.isdigit():
        raise SystemExit(f"recuento no numérico en línea {i}: {rec!r}")
    npreg = row["N.º de pregunta"]
    if tipo == "RESPUESTA_EDAD":
        nivel = row["Edad"].strip()
        etiqueta = row["Edad"].strip()
    else:
        nivel = row["Valor"].strip()
        etiqueta = row["Respuesta"].strip() or row["Valor"].strip()
    pct_src = (row["Porcentaje"] or "").strip()
    freq_rows.append({
        "linea_archivo": i,
        "orden": row["Orden"],
        "parte": row["Parte"],
        "n_pregunta": npreg,
        "pregunta": row["Pregunta"],
        "tipo": tipo,
        "nivel": nivel,
        "etiqueta": etiqueta,
        "frecuencia": int(rec),
        "n": 39,
        "porcentaje_fuente": pct_src,
        "nota": "agregado del registro oficial; no es microdato",
    })

by_q = {}
for r in freq_rows:
    by_q.setdefault(r["n_pregunta"], []).append(r)
errors = []
for q, rs in by_q.items():
    s = sum(r["frecuencia"] for r in rs)
    if s != 39:
        errors.append(f"pregunta {q} suma {s}")
if errors:
    raise SystemExit("; ".join(errors))

freq_path = DATOS / "base_frecuencias_n39.csv"
with freq_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(freq_rows[0].keys()))
    w.writeheader()
    w.writerows(freq_rows)

# plantilla del protocolo original: sigue vacía. Este CSV no trae BFI ni CAM.
plantilla = DATOS / "plantilla_vacia_protocolo_original.csv"
with plantilla.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "codigo_anonimo", "consentimiento", "condicion",
        "bfi_4", "bfi_9", "bfi_11", "bfi_17", "bfi_23", "bfi_25",
        "responsabilidad_media", "cam_error_total_pct", "cam_rt_total_ms",
    ])

meta = {
    "fuente": str(SRC),
    "sha256": sha,
    "bytes": len(raw),
    "filas_datos": len(rows),
    "filas_frecuencia": len(freq_rows),
    "preguntas": {q: sum(r["frecuencia"] for r in rs) for q, rs in by_q.items()},
    "microdatos": False,
}
(DATOS / "integridad_fuente.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(meta, ensure_ascii=False, indent=2))
