#!/usr/bin/env bash
set -Eeuo pipefail

REPO="$GITHUB_WORKSPACE"
TASK="$REPO/factory-runs/concentracion-39-u3-u4"
TEMP_ROOT="$RUNNER_TEMP/concentracion-39-u3-u4"
OUTPUT="$TASK/deliverables"
mkdir -p "$TEMP_ROOT" "$OUTPUT/evidence"
cp -a "$TASK/." "$TEMP_ROOT/"
T="$TEMP_ROOT"
python3 "$T/prepare_sheets.py"

# Pandoc resolves relative Markdown image paths from the repository root.
mkdir -p "$REPO/assets"
cp -a "$T/assets/." "$REPO/assets/"

python3 -B "$REPO/document-factory/src/selftest.py"
python3 -B "$REPO/document-factory/src/factory.py" validate-profile "$TASK/profiles/profile-entrega3.json" --repo-root "$REPO"
python3 -B "$REPO/document-factory/src/factory.py" validate-profile "$TASK/profiles/profile-entrega4.json" --repo-root "$REPO"

build_one() {
  local name="$1" profile="$2" kind="$3" stem="$4" page_limit="$5"
  local workspace="$T/workspaces/$name"
  local profile_path="$TASK/profiles/$profile"
  local docx="$workspace/build/report.docx"
  local pdf="$workspace/build/report.pdf"
  local xlsx="$workspace/build/evidence.xlsx"

  echo "FACTORY_BUILD_START=$name"
  if ! python3 -B "$REPO/document-factory/src/factory.py" build "$workspace" "$profile_path" --repo-root "$REPO"; then
    echo "FACTORY_BUILD_DIAGNOSTICS=$name" >&2
    for log in "$workspace"/evidence/logs/*.stderr.txt "$workspace"/evidence/logs/*.stdout.txt; do
      if [ -f "$log" ]; then
        echo "===== $log =====" >&2
        cat "$log" >&2
      fi
    done
    exit 41
  fi
  python3 -B "$REPO/factory-runs/metodologia-cuantitativa-u3-u4/format_docx.py" "$docx" "$workspace/evidence/formatting.json" "$kind"
  rm -f "$pdf"
  soffice --headless --convert-to pdf --outdir "$workspace/build" "$docx" >/dev/null
  test -s "$docx" && test -s "$pdf"

  local pages
  pages="$(pdfinfo "$pdf" | awk '/^Pages:/ {print $2}')"
  echo "FACTORY_PAGES_$name=$pages"
  if [ -n "$page_limit" ] && [ "$pages" -gt "$page_limit" ]; then
    echo "PAGE_LIMIT_FAIL:$name:$pages:$page_limit" >&2
    exit 31
  fi

  python3 -B "$REPO/document-factory/src/factory.py" validate "$workspace" "$profile_path" --repo-root "$REPO"
  python3 -B "$REPO/document-factory/src/factory.py" self-audit "$workspace" "$profile_path"
  python3 -B "$REPO/document-factory/src/factory.py" freeze "$workspace"

  python3 - "$docx" "$name" <<'PY'
import sys, zipfile
docx, name = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(docx) as z:
    assert z.testzip() is None
    names = z.namelist()
    assert "word/document.xml" in names
    if name == "entrega4-resultados":
        media = [n for n in names if n.startswith("word/media/") and n.lower().endswith(".png")]
        assert len(media) >= 3, f"expected 3 embedded PNGs, found {len(media)}"
        for n in media:
            assert z.getinfo(n).file_size > 10000, n
        print("EMBEDDED_OFFICIAL_SCREENSHOTS=PASS", len(media))
PY

  cp "$docx" "$OUTPUT/$stem.docx"
  cp "$pdf" "$OUTPUT/$stem.pdf"
  if [ "$name" = "entrega3-base" ] || [ "$name" = "entrega4-resultados" ]; then
    cp "$xlsx" "$OUTPUT/$stem.xlsx"
  fi
  mkdir -p "$OUTPUT/evidence/$name"
  cp -a "$workspace/evidence/." "$OUTPUT/evidence/$name/"
  cp "$workspace/FROZEN_CANDIDATE.json" "$OUTPUT/evidence/$name/"
  printf '%s\t%s\t%s\n' "$name" "$pages" "$(sha256sum "$docx" | cut -d' ' -f1)" >> "$T/page-and-hash-ledger.tsv"
  echo "FACTORY_BUILD_PASS=$name"
}

build_one "entrega3-base" "profile-entrega3.json" "ENTREGA3" "01_Entrega3_Base_de_Datos_Organizada" ""
build_one "entrega3-informe" "profile-entrega3.json" "ENTREGA3" "02_Entrega3_Informe_de_Campo" "2"
build_one "entrega4-resultados" "profile-entrega4.json" "ENTREGA4" "03_Entrega4_Resultados_y_Evidencia" "10"
build_one "entrega4-informe" "profile-entrega4.json" "ENTREGA4" "04_Entrega4_Informe_Analitico" "10"

cp "$TASK/data/base_frecuencias_n39.csv" "$OUTPUT/"
cp "$TASK/data/descriptivos_R_4_5_3.csv" "$OUTPUT/"
cp "$TASK/data/descriptivos_jamovi_jmv.csv" "$OUTPUT/"
cp "$TASK/data/descriptivos_jasp.csv" "$OUTPUT/"
cp "$T/page-and-hash-ledger.tsv" "$OUTPUT/"

python3 - "$OUTPUT" <<'PY'
import hashlib, json, sys
from pathlib import Path
out=Path(sys.argv[1])
rows=[]
for p in sorted(out.rglob("*")):
    if p.is_file() and p.name != "manifest.json":
        rows.append({"path":p.relative_to(out).as_posix(),"size_bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
obj={
 "schema":"UNIACC_DOCUMENT_FACTORY_DELIVERY/1.0",
 "task":"concentracion-39-u3-u4",
 "status":"BUILT_AND_STRUCTURALLY_VALIDATED",
 "n_per_question":39,
 "question_count":6,
 "source_type":"AGGREGATED_MARGINAL_FREQUENCIES",
 "individual_linked_microdata":"NOT_AVAILABLE",
 "screenshots_embedded":["RStudio","jamovi","JASP"],
 "jamovi_jasp_native_project_files":"NOT_PRODUCED; screenshots contain loaded outputs from their respective statistical engines",
 "G23":"NOT_EXECUTED",
 "G24":"NOT_EXECUTED",
 "certification":"NOT_CLAIMED",
 "artifacts":rows
}
(out/"manifest.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("DELIVERY_MANIFEST=PASS; FILES=",len(rows))
PY

echo "ALL_FOUR_DOCUMENTS_BUILT=PASS"
