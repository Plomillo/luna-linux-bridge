#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

VERSION="$CALIBRE_VERSION"
ARCH="$CALIBRE_ARCH"
WORK_ROOT="$RUNNER_TEMP/cajita-calibre-compact"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CANDIDATE_DIR="$REPO_ROOT/cajita-candidates/calibre-compact"
DOWNLOAD_DIR="$WORK_ROOT/download"
STAGE="$WORK_ROOT/root"
OUT_DIR="$WORK_ROOT/output"
EVIDENCE_DIR="$WORK_ROOT/evidence"
ARCHIVE="$OUT_DIR/calibre-compact-$VERSION-linux-$ARCH.tar.xz"
SOURCE_ARCHIVE="$DOWNLOAD_DIR/calibre-$VERSION-$ARCH.txz"
SIDECAR="$DOWNLOAD_DIR/calibre-$VERSION-$ARCH.txz.sha512"

rm -rf "$WORK_ROOT"
mkdir -p "$DOWNLOAD_DIR" "$STAGE" "$OUT_DIR" "$EVIDENCE_DIR"

SOURCE_URL="https://download.calibre-ebook.com/$VERSION/calibre-$VERSION-$ARCH.txz"
SIDECAR_URL="https://calibre-ebook.com/signatures/calibre-$VERSION-$ARCH.txz.sha512"

curl --fail --location --retry 3 --retry-all-errors --proto '=https' --tlsv1.2 "$SOURCE_URL" -o "$SOURCE_ARCHIVE"
curl --fail --location --retry 3 --retry-all-errors --proto '=https' --tlsv1.2 "$SIDECAR_URL" -o "$SIDECAR"

EXPECTED_SHA512="$(awk 'NR==1 {print $1}' "$SIDECAR" | tr -d '\r\n')"
if [[ ! "$EXPECTED_SHA512" =~ ^[a-fA-F0-9]{128}$ ]]; then
  echo "FAIL_CLOSED: no se pudo interpretar el SHA-512 oficial." >&2
  cat "$SIDECAR" >&2
  exit 21
fi
printf '%s  %s\n' "$EXPECTED_SHA512" "$SOURCE_ARCHIVE" | sha512sum --check --status || {
  echo "FAIL_CLOSED: SHA-512 del binario oficial no coincide." >&2
  exit 22
}

tar --extract --xz --file "$SOURCE_ARCHIVE" --directory "$STAGE" --no-same-owner
test -f "$STAGE/ebook-convert"
test -f "$STAGE/calibre-parallel"
test -f "$STAGE/calibre_postinstall"
chmod +x "$STAGE/ebook-convert" "$STAGE/calibre-parallel" "$STAGE/calibre_postinstall"

export CALIBRE_UPSTREAM_VERSION="$VERSION"
export CALIBRE_EBOOK_CONVERT="$STAGE/ebook-convert"
export QT_QPA_PLATFORM=offscreen
export QTWEBENGINE_DISABLE_SANDBOX=1
export CALIBRE_CONFIG_DIRECTORY="$WORK_ROOT/calibre-config"
mkdir -p "$CALIBRE_CONFIG_DIRECTORY"

"$STAGE/ebook-convert" --version

python3 "$CANDIDATE_DIR/prune_runtime.py" \
  --root "$STAGE" \
  --report "$EVIDENCE_DIR/prune-report.json" \
  --apply

python3 -m unittest discover -s "$CANDIDATE_DIR/tests" -v

cat > "$WORK_ROOT/fixture.html" <<'HTML'
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Prueba Cajita Calibre</title></head>
<body>
<h1>Prueba de conversión</h1>
<p>La Cajita de Luna convierte PDF y EPUB conservando información textual básica.</p>
<p>Integridad, capítulo, acentuación: áéíóú ñ. Ruta operativa verificada.</p>
</body>
</html>
HTML

export CALIBRE_COMPACT_AUDIT_LOG="$EVIDENCE_DIR/conversion-audit.jsonl"
python3 "$CANDIDATE_DIR/calibre_compact.py" "$WORK_ROOT/fixture.html" "$WORK_ROOT/from-html.epub"
python3 "$CANDIDATE_DIR/calibre_compact.py" "$WORK_ROOT/fixture.html" "$WORK_ROOT/from-html.pdf"
pdftotext "$WORK_ROOT/from-html.pdf" "$WORK_ROOT/from-html.txt"
grep -q "Integridad" "$WORK_ROOT/from-html.txt"
grep -q "acentuación" "$WORK_ROOT/from-html.txt"
python3 "$CANDIDATE_DIR/calibre_compact.py" "$WORK_ROOT/from-html.epub" "$WORK_ROOT/from-epub.pdf"
python3 "$CANDIDATE_DIR/calibre_compact.py" "$WORK_ROOT/from-epub.pdf" "$WORK_ROOT/from-pdf.epub"

python3 - "$WORK_ROOT/from-html.epub" "$WORK_ROOT/from-pdf.epub" <<'PY'
from pathlib import Path
import sys
import zipfile

for name in sys.argv[1:]:
    path = Path(name)
    with zipfile.ZipFile(path) as archive:
        texts = []
        for member in archive.namelist():
            if member.lower().endswith((".xhtml", ".html", ".htm")):
                try:
                    texts.append(archive.read(member).decode("utf-8", errors="ignore"))
                except KeyError:
                    pass
        joined = "\n".join(texts)
        for marker in ("Integridad", "acentuación"):
            if marker not in joined:
                raise SystemExit(f"Falta el texto esperado {marker!r} en {path.name}")
PY

if python3 "$CANDIDATE_DIR/calibre_compact.py" "$WORK_ROOT/from-html.epub" "$WORK_ROOT/should-not-create.mobi"; then
  echo "FAIL_CLOSED: el wrapper aceptó una salida .mobi." >&2
  exit 23
fi
test ! -e "$WORK_ROOT/should-not-create.mobi"

python3 - "$WORK_ROOT" "$EVIDENCE_DIR" "$VERSION" "$ARCH" "$EXPECTED_SHA512" "$SOURCE_URL" "$SOURCE_ARCHIVE" "$STAGE" "$ARCHIVE" <<'PY'
import hashlib, json, sys, tarfile
from pathlib import Path
work, evidence_dir, version, arch, source_sha512, source_url, source_archive, stage, archive = map(str, sys.argv[1:])
work, evidence_dir, source_archive, stage, archive = map(Path, (work, evidence_dir, source_archive, stage, archive))
def digest(path, algorithm="sha256"):
    h=hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()
def tree_size(root):
    total=0; count=0
    for p in root.rglob("*"):
        if p.is_file() and not p.is_symlink():
            total += p.stat().st_size; count += 1
    return count,total
file_count, raw_bytes = tree_size(stage)
archive.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(archive, "w:xz", preset=9) as tf:
    for p in sorted(stage.rglob("*")):
        arc = p.relative_to(stage)
        tf.add(p, arcname=str(arc), recursive=False)
report = {
    "schema":"CAJITA_CALIBRE_COMPACT_BUILD_EVIDENCE/1.0",
    "candidate_id":"CAJITA_CALIBRE_COMPACT_V1_LINUX_X86_64",
    "upstream":{"project":"Calibre","version":version,"architecture":arch,"source_url":source_url,"source_sha512":source_sha512,"source_sha256":digest(source_archive),"sidecar_status":"SHA512_VERIFIED"},
    "pruning":{"report_file":"prune-report.json","status":"APPLIED_AND_SMOKE_TESTED"},
    "runtime":{"file_count":file_count,"raw_bytes":raw_bytes,"archive_bytes":archive.stat().st_size,"archive_sha256":digest(archive),"archive_name":archive.name},
    "functional_tests":{"unit_tests":"PASS","html_to_epub":"PASS","epub_to_pdf":"PASS","pdf_to_epub":"PASS","html_to_pdf":"PASS","pdf_text_and_accents":"PASS","epub_text_and_accents":"PASS","unsupported_output_rejected":"PASS"},
    "conversion_audit":"conversion-audit.jsonl",
    "integration":{"global_cap_bytes":470000000,"macrodown_inclusion":"NOT_AUTOMATIC","raw_size_gate":"PASS" if raw_bytes <= 470000000 else "FAIL_REQUIRES_MORE_COMPACTION_OR_SEPARATE_PAYLOAD","size_gate":"MEASURED_CANDIDATE_REQUIRES_GLOBAL_REBALANCE","certification":"NOT_GRANTED"},
}
(evidence_dir/"build-evidence.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False))
if raw_bytes > 470000000:
    print("NOTICE: candidate raw footprint exceeds Cajita global cap; do not integrate.")
PY

printf '\nCALIBRE_COMPACT_ARTIFACT=%s\n' "$ARCHIVE"
printf 'CALIBRE_COMPACT_EVIDENCE=%s\n' "$EVIDENCE_DIR/build-evidence.json"
