#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, re, subprocess, sys, zipfile
from xml.etree import ElementTree as ET

RUN = pathlib.Path(__file__).resolve().parent
REPO = RUN.parents[1]
sys.path.insert(0, str(REPO / "document-factory" / "src"))
from factory import body_word_count, validate_profile
from source_pipeline import validate_ledger, validate_citations

PROFILE = RUN / "profile.json"
REPORT = RUN / "source" / "report.md"
LEDGER = RUN / "workspace" / "data" / "source-ledger.json"
DOCX = RUN / "deliverables" / "latest" / "Trabajo1_DiegoIgnacioNorambuenaMiranda.docx"
PDF = RUN / "deliverables" / "latest" / "Trabajo1_DiegoIgnacioNorambuenaMiranda.pdf"
SOURCE_PDF = RUN / "sources" / "Guia de la buena esposa.pdf"
EVIDENCE = RUN / "evidence"

def output(cmd):
    return subprocess.run(cmd, text=True, capture_output=True, check=True).stdout

def main():
    profile, failures = validate_profile(PROFILE, REPO)
    assert not failures, failures
    rubric = profile["rubric"]
    assert len(rubric["criteria"]) == 6
    assert abs(sum(float(x["points"]) for x in rubric["criteria"]) - 26.25) < 1e-9
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    ledger_result = validate_ledger(ledger, 5)
    assert ledger_result["status"] == "PASS", ledger_result
    report = REPORT.read_text(encoding="utf-8")
    citation_result = validate_citations(report, ledger)
    assert citation_result["status"] == "PASS", citation_result
    words = body_word_count(REPORT)
    assert 1100 <= words <= 1600, f"BODY_WORD_COUNT:{words}"
    assert SOURCE_PDF.is_file() and SOURCE_PDF.read_bytes().startswith(b"%PDF-")
    source_hash = hashlib.sha256(SOURCE_PDF.read_bytes()).hexdigest()
    assert source_hash == "ccb0979322fceba254e01c4eb5b5a8d5954326eaa0112c414ac635ff27626c5f"
    source_info = output(["pdfinfo", str(SOURCE_PDF)])
    assert re.search(r"^Pages:\s+14\s*$", source_info, re.M), "SOURCE_PDF_NOT_14_PAGES"
    pdfinfo = output(["pdfinfo", str(PDF)])
    page_match = re.search(r"^Pages:\s+(\d+)\s*$", pdfinfo, re.M)
    pages = int(page_match.group(1)) if page_match else -1
    assert pages == 6, f"TOTAL_PAGES:{pages}"
    page_texts = [output(["pdftotext", "-f", str(n), "-l", str(n), "-layout", str(PDF), "-"]) for n in range(1, 7)]
    checks = {
      1:["UNIVERSIDAD UNIACC","PSICOLOGIA SOCIAL"],
      2:["Introducción","BUENHOGAR"],
      3:["Desarrollo","reglas 9, 10 y 11","Extra"],
      4:["psicología social","Moscovici"],
      5:["Conformidad y obediencia","Conclusión","Milgram"],
      6:["Referencias","Asch","Bandura"]
    }
    for page, tokens in checks.items():
        normalized = " ".join(page_texts[page-1].casefold().split())
        for token in tokens:
            assert token.casefold() in normalized, f"PAGE_{page}_MISSING:{token}"
    body_text = " ".join(" ".join(page_texts[1:5]).casefold().split())
    for token in ["preparar el plato favorito","arreglarse para recibirlo","dulce e interesante","mantener la casa impecable","ambiente de descanso","asear y vestir a los niños","reducir los ruidos","recibirlo con una sonrisa","reglas 9, 10 y 11","apartado «extra»","cuál es su lugar"]:
        assert token.casefold() in body_text, "CASE_COVERAGE_MISSING:" + token
    assert DOCX.is_file() and DOCX.stat().st_size > 5000
    with zipfile.ZipFile(DOCX) as package:
        assert package.testzip() is None
        names = package.namelist()
        assert "word/document.xml" in names
        xml = package.read("word/document.xml").decode("utf-8")
        styles_root = ET.fromstring(package.read("word/styles.xml"))
        ns = {"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        style_rows = {row.attrib.get("{%s}styleId" % ns["w"]): row for row in styles_root.findall("w:style", ns)}
        def style_size(style_id):
            row = style_rows[style_id]
            node = row.find(".//w:sz", ns)
            return node.attrib.get("{%s}val" % ns["w"]) if node is not None else None
        def style_font(style_id):
            row = style_rows[style_id]
            node = row.find(".//w:rFonts", ns)
            return node.attrib.get("{%s}ascii" % ns["w"]) if node is not None else None
        assert style_font("Normal") == "Arial" and style_font("BodyText") == "Arial", "ARIAL_BODY_FONT_FAIL"
        assert style_font("Heading1") == "Arial" and style_font("Heading2") == "Arial", "ARIAL_HEADING_FONT_FAIL"
        assert style_size("Normal") == "24" and style_size("BodyText") == "24", "BODY_NOT_12PT"
        assert style_size("Heading1") == "32" and style_size("Heading2") == "32", "HEADING_NOT_16PT"
        body_style = style_rows["BodyText"]
        line = body_style.find("w:pPr/w:spacing", ns)
        align = body_style.find("w:pPr/w:jc", ns)
        assert line is not None and line.attrib.get("{%s}line" % ns["w"]) == "360", "ONE_AND_HALF_LINE_SPACING_MISSING"
        assert align is not None and align.attrib.get("{%s}val" % ns["w"]) == "both", "BODY_NOT_JUSTIFIED"
        hanging_styles = []
        for style_id, row in style_rows.items():
            ind = row.find("w:pPr/w:ind", ns)
            if ind is not None and ind.attrib.get("{%s}hanging" % ns["w"]) == "720":
                hanging_styles.append(style_id)
        assert hanging_styles, "APA_HANGING_INDENT_MISSING"
        margins = re.findall(r'<w:pgMar[^>]*/>', xml)
        assert margins and all(str(x) in margins[0] for x in ['w:top="1417"','w:bottom="1417"','w:left="1417"','w:right="1417"']), "MARGINS_NOT_2_5CM"
    result = {
      "schema":"UNIT1_DOCUMENT_VERIFICATION/1.0",
      "status":"PASS",
      "rubric_points":26.25,
      "rubric_criteria":6,
      "total_pages":pages,
      "body_pages":4,
      "development_pages":3,
      "body_word_count":words,
      "source_pdf_pages":14,
      "source_pdf_sha256":source_hash,
      "verified_sources":ledger_result["distinct_verified"],
      "citation_ids":citation_result["cited_ids"],
      "checks":{"page_map":"PASS","case_rules_1_to_11_extra_final_image":"PASS","Arial_12_16":"PASS","line_spacing_1_5":"PASS","margins_2_5cm":"PASS","rubric_sum":"PASS","citation_ledger":"PASS"},
      "human_gates":{"deadline_submission":"PENDING_USER","language_final_review":"PENDING_TEACHER","rubric_content_grade":"PENDING_TEACHER","G23":"NOT_EXECUTED","G24":"NOT_EXECUTED"},
      "certification_authority":False
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
