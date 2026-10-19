from __future__ import annotations
import json, pathlib, re, subprocess, sys, zipfile
from docx import Document

if len(sys.argv) not in (3, 4):
    raise SystemExit("USAGE: verify_document.py WORKSPACE PROFILE_PATH [REPO_ROOT]")
root = pathlib.Path(sys.argv[1]).resolve()
profile_path = pathlib.Path(sys.argv[2]).resolve()
repo_root = pathlib.Path(sys.argv[3]).resolve() if len(sys.argv) == 4 else pathlib.Path.cwd()
if not profile_path.is_file():
    raise SystemExit("PROFILE_NOT_FOUND:" + str(profile_path))
docx = root / "build" / "report.docx"
pdf = root / "build" / "report.pdf"
if not docx.is_file() or not pdf.is_file() or docx.stat().st_size < 10000:
    raise SystemExit("DELIVERABLE_MISSING_OR_SUSPICIOUS_SIZE")

profile = json.loads(profile_path.read_text(encoding="utf-8"))
info = subprocess.run(["pdfinfo", str(pdf)], text=True, capture_output=True, check=True).stdout
match = re.search(r"^Pages:\s+(\d+)\s*$", info, re.M)
if not match:
    raise SystemExit("PDF_PAGE_COUNT_UNREADABLE")
pages = int(match.group(1))
if pages != 6:
    raise SystemExit(f"TOTAL_PAGES_NOT_SIX:{pages}")

expected = [
    (1, ["PSICOLOGÍA", "IDENTIFICACIÓN DE LOS ENFOQUES", "Diego Ignacio Norambuena Miranda"]),
    (2, ["Pregunta 1.", "positivismo lógico"]),
    (3, ["Pregunta 2.", "Kuhn"]),
    (4, ["Pregunta 3.", "Quine"]),
    (5, ["Pregunta 4.", "Nersessian"]),
    (6, ["Referencias", "Bird", "Creath", "Kuhn", "Nersessian", "Quine"])
]
page_texts = []
for page_number in range(1, 7):
    p = subprocess.run(["pdftotext", "-f", str(page_number), "-l", str(page_number), "-layout", str(pdf), "-"], text=True, capture_output=True, check=True)
    page_texts.append(p.stdout)
failures = []
for number, tokens in expected:
    norm = " ".join(page_texts[number - 1].casefold().split())
    for token in tokens:
        if token.casefold() not in norm:
            failures.append(f"PAGE_{number}_MISSING:{token}")
if failures:
    raise SystemExit("PAGE_STRUCTURE_FAIL:" + ";".join(failures))

ledger_path = root / "data" / "source-ledger.json"
if not ledger_path.is_file():
    raise SystemExit("SOURCE_LEDGER_NOT_FOUND")
ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
source_ids = {str(row.get("source_id")) for row in ledger.get("sources", []) if row.get("verified") is True and row.get("source_id")}
minimum_sources = int(profile["required_research"]["minimum_distinct_sources"])
if len(source_ids) < minimum_sources:
    raise SystemExit(f"SOURCE_LEDGER_MINIMUM_NOT_MET:{len(source_ids)}<{minimum_sources}")

sys.path.insert(0, str(repo_root / "document-factory" / "src"))
from source_pipeline import validate_ledger, validate_citations
ledger_validation = validate_ledger(ledger, minimum_sources)
if ledger_validation["status"] != "PASS":
    raise SystemExit("SOURCE_LEDGER_INVALID:" + ";".join(ledger_validation["failures"]))
report = (root / "source" / "report.md").read_text(encoding="utf-8")
citation_validation = validate_citations(report, ledger)
if citation_validation["status"] != "PASS":
    raise SystemExit("CITATION_LEDGER_MISMATCH:" + ";".join(citation_validation["failures"]))
for term in ("(Creath, 2022)", "(Kuhn, 2012)", "(Quine, 1951)", "(Quine, 1969)", "(Nersessian, 1992, 1999)"):
    if term not in report:
        raise SystemExit("APA_IN_TEXT_CITATION_MISSING:" + term)

with zipfile.ZipFile(docx) as package:
    media = [x for x in package.namelist() if x.startswith("word/media/")]
if not media:
    raise SystemExit("COVER_LOGO_MISSING_FROM_DOCX")

doc = Document(str(docx))
for idx, section in enumerate(doc.sections, 1):
    margins = [section.top_margin, section.bottom_margin, section.left_margin, section.right_margin]
    if any(abs((m.inches * 2.54) - 2.5) > 0.03 for m in margins):
        raise SystemExit(f"MARGIN_CHECK_FAIL_SECTION_{idx}")
normal = doc.styles["Normal"]
if normal.font.name != "Arial" or normal.font.size is None or abs(normal.font.size.pt - 12) > 0.01:
    raise SystemExit("BODY_FONT_CHECK_FAIL")
if abs(float(normal.paragraph_format.line_spacing) - 1.5) > 0.01:
    raise SystemExit("LINE_SPACING_CHECK_FAIL")

result = {
    "schema": "UNIT2_EPISTEMOLOGY_DOCUMENT_VERIFICATION/1.1",
    "status": "PASS",
    "total_pdf_pages": pages,
    "page_map": {"1":"cover", "2":"question_1", "3":"question_2", "4":"question_3", "5":"question_4", "6":"references"},
    "verified_sources": len(source_ids),
    "citation_ledger": citation_validation["status"],
    "cover_logo_embedded": True,
    "docx_bytes": docx.stat().st_size,
    "pdf_bytes": pdf.stat().st_size,
    "apa_in_text_markers_checked": 5,
    "font": "Arial",
    "body_size_pt": 12,
    "line_spacing": 1.5,
    "margins_cm": 2.5,
    "g23": "NOT_EXECUTED",
    "g24": "NOT_EXECUTED",
    "teacher_review": "PENDING"
}
(root / "evidence").mkdir(parents=True, exist_ok=True)
(root / "evidence" / "document-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
