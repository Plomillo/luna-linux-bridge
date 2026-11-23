#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, json, pathlib, re, subprocess, sys, zipfile
from xml.etree import ElementTree as ET

RUN = pathlib.Path(__file__).resolve().parent
REPO = RUN.parents[1]
sys.path.insert(0, str(REPO / "document-factory" / "src"))
from factory import validate_profile
from rubric_compiler import compile_rubric
from source_pipeline import validate_ledger, validate_citations

PROFILE = RUN / "profile.json"
REPORT = RUN / "source" / "report.md"
LEDGER = RUN / "workspace" / "data" / "source-ledger.json"
SOURCE_PDF = RUN / "sources" / "Guia de la buena esposa.pdf"
DOCX = RUN / "deliverables" / "latest" / "Trabajo1_DiegoIgnacioNorambuenaMiranda.docx"
PDF = RUN / "deliverables" / "latest" / "Trabajo1_DiegoIgnacioNorambuenaMiranda.pdf"
EVIDENCE = RUN / "evidence"
WORK = RUN / "workspace" / "build"

def run(cmd):
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"COMMAND_FAILED:{cmd}\nSTDOUT:{p.stdout[-4000:]}\nSTDERR:{p.stderr[-4000:]}")
    return p.stdout

def render_blocks(markdown):
    out, buffer, in_references = [], [], False
    def flush():
        nonlocal buffer
        if buffer:
            text = re.sub(r"\[@[A-Za-z0-9_.:-]+(?:[^\]]*)\]", "", " ".join(buffer))
            text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", html.escape(" ".join(text.split())))
            cls = "reference" if in_references else "body"
            out.append(f'<p class="{cls}">{text}</p>')
            buffer = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line == "<!-- PAGEBREAK -->":
            flush()
            out.append('<p class="page-break">&nbsp;</p>')
            continue
        if line.startswith("<!--") and line.endswith("-->"):
            flush()
            continue
        if line.startswith("# "):
            flush()
            title = line[2:].strip()
            if title.casefold() == "referencias":
                in_references = True
            out.append(f"<h1>{html.escape(title)}</h1>")
            continue
        if line.startswith("## "):
            flush()
            out.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
            continue
        buffer.append(line)
    flush()
    return "\n".join(out)

def main():
    WORK.mkdir(parents=True, exist_ok=True)
    DOCX.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    profile, failures = validate_profile(PROFILE, REPO)
    if failures:
        raise SystemExit("PROFILE_INVALID:" + ";".join(failures))
    rubric = compile_rubric(profile)
    if rubric["criterion_count"] != 6 or abs(rubric["declared_total_points"] - 26.25) > 1e-9:
        raise SystemExit("RUBRIC_NOT_MATCHING_PLATFORM:EXPECTED_6_CRITERIA_26_25")
    (EVIDENCE / "rubric-obligations.json").write_text(json.dumps(rubric, ensure_ascii=False, indent=2) + "\n")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    ledger_check = validate_ledger(ledger, profile["required_research"]["minimum_distinct_sources"])
    report = REPORT.read_text(encoding="utf-8")
    citation_check = validate_citations(report, ledger)
    if ledger_check["status"] != "PASS":
        raise SystemExit("SOURCE_LEDGER_FAIL:" + ";".join(ledger_check["failures"]))
    if citation_check["status"] != "PASS":
        raise SystemExit("CITATION_LEDGER_FAIL:" + ";".join(citation_check["failures"]))
    source_hash = hashlib.sha256(SOURCE_PDF.read_bytes()).hexdigest()
    if source_hash != "ccb0979322fceba254e01c4eb5b5a8d5954326eaa0112c414ac635ff27626c5f":
        raise SystemExit("PRIMARY_SOURCE_HASH_MISMATCH")
    cover = """
    <div class="cover">
      <p class="institution">UNIVERSIDAD UNIACC</p>
      <p class="course">PSICOLOGIA SOCIAL - 388 - 487999</p>
      <div class="cover-title">
        <h1>COMPORTAMIENTO Y GÉNERO</h1>
        <p class="subtitle">Análisis de la «Guía de la buena esposa»</p>
      </div>
      <div class="cover-meta">
        <p>Estudiante: Diego Ignacio Norambuena Miranda</p>
        <p>Docente: _____________________________________________</p>
        <p>Fecha: 22 de noviembre de 2026</p>
      </div>
    </div>
    """
    before, after = report.split("<!-- BODY_START -->", 1)
    body_source, reference_source = after.split("<!-- BODY_END -->", 1)
    body = render_blocks(body_source) + render_blocks(reference_source)
    document = f'''<!DOCTYPE html><html><head><meta charset="utf-8">
    <meta name="author" content="Universidad UNIACC - Psicología Social">
    <meta name="title" content="Comportamiento y género">
    <style>
      @page {{ size: A4; margin: 2.5cm; }}
      html, body {{ font-family: Arial; font-size: 12pt; color: #000; }}
      body {{ line-height: 1.5; }}
      p {{ font-family: Arial; font-size: 12pt; line-height: 1.5; text-align: justify; text-indent: 1.25cm; margin: 0 0 6pt 0; }}
      h1, h2 {{ font-family: Arial; font-size: 16pt; font-weight: bold; text-align: center; line-height: 1.5; margin: 0 0 8pt 0; page-break-after: avoid; }}
      h2 {{ margin-top: 4pt; }}
      em {{ font-style: italic; }}
      .page-break {{ page-break-before: always; break-before: page; height: 1pt; margin: 0; padding: 0; line-height: 1pt; font-size: 1pt; }}
      .cover {{ page-break-after: always; break-after: page; text-align: center; padding-top: 1cm; }}
      .cover p {{ text-align: center; text-indent: 0; margin-bottom: 10pt; }}
      .institution {{ font-size: 16pt; font-weight: bold; }}
      .course {{ margin-top: 20pt; }}
      .cover-title {{ margin-top: 2.5cm; }}
      .cover-title h1 {{ font-size: 16pt; }}
      .subtitle {{ font-size: 12pt; }}
      .cover-meta {{ margin-top: 2cm; }}
      .cover-meta p {{ text-align: left; margin-left: 2cm; }}
      p.reference {{ text-indent: -1.27cm; margin-left: 1.27cm; text-align: left; margin-bottom: 8pt; }}
    </style></head><body>{cover}<p class="page-break">&nbsp;</p>{body}</body></html>'''
    html_path = WORK / "report.html"
    html_path.write_text(document, encoding="utf-8")
    profile_uri = "file:///tmp/lo-unit1-" + str(hashlib.sha256(str(RUN).encode()).hexdigest()[:12])
    # Remove stale outputs so a rebuild cannot silently retain a previous candidate.
    DOCX.unlink(missing_ok=True)
    PDF.unlink(missing_ok=True)
    candidate = DOCX.parent / "report.docx"
    candidate.unlink(missing_ok=True)
    run(["soffice", "--headless", "-env:UserInstallation=" + profile_uri, "--convert-to", "docx:Office Open XML Text", "--outdir", str(DOCX.parent), str(html_path)])
    if candidate.is_file():
        candidate.replace(DOCX)
    if not DOCX.is_file():
        raise SystemExit("DOCX_BUILD_MISSING")
    candidate_pdf = DOCX.parent / (DOCX.stem + ".pdf")
    candidate_pdf.unlink(missing_ok=True)
    run(["soffice", "--headless", "-env:UserInstallation=" + profile_uri, "--convert-to", "pdf", "--outdir", str(DOCX.parent), str(DOCX)])
    if candidate_pdf.is_file() and candidate_pdf != PDF:
        candidate_pdf.replace(PDF)
    if not PDF.is_file():
        raise SystemExit("PDF_BUILD_MISSING")
    pdfinfo = run(["pdfinfo", str(PDF)])
    m = re.search(r"^Pages:\s+(\d+)\s*$", pdfinfo, re.M)
    pages = int(m.group(1)) if m else -1
    result = {
      "schema":"UNIT1_DOCUMENT_FACTORY_BUILD/1.0",
      "status":"PASS" if pages == 6 else "FAIL",
      "rubric_total":rubric["declared_total_points"],
      "rubric_criteria":rubric["criterion_count"],
      "source_pdf_sha256":source_hash,
      "source_ledger":ledger_check,
      "citation_ledger":citation_check,
      "total_pages":pages,
      "required_total_pages":6,
      "required_body_pages":4,
      "docx_bytes":DOCX.stat().st_size,
      "pdf_bytes":PDF.stat().st_size
    }
    (EVIDENCE / "build.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if pages != 6:
        raise SystemExit("PAGE_COUNT_MISMATCH_EXPECTED_6_GOT_" + str(pages))

if __name__ == "__main__":
    main()
