from pathlib import Path
import json
import fitz
from louksna_docworkbench.reading_edition import analyze_pdf_order, create_safe_ordered_copy, create_academic_reading_edition

def make_pdf(path: Path, pages: list[tuple[str, int | None]]) -> None:
    doc=fitz.open()
    for text,folio in pages:
        page=doc.new_page(); page.insert_text((70,75),text,fontsize=12)
        if folio is not None: page.insert_text((285,810),str(folio),fontsize=9)
    doc.save(path); doc.close()

def test_reorders_when_folios_prove_complete_permutation(tmp_path):
    src=tmp_path/"scrambled.pdf"; out=tmp_path/"ordered.pdf"; a=tmp_path/"a.json"; audit=tmp_path/"out.json"
    make_pdf(src,[("PAGE_ALPHA",12),("PAGE_BETA",10),("PAGE_GAMMA",11)])
    data=analyze_pdf_order(src)
    assert data["recommendation"]=="ORDER_BY_PRINTED_FOLIO"
    assert data["recommended_page_order_1_based"]==[2,3,1]
    a.write_text(json.dumps(data),encoding="utf-8")
    result=create_safe_ordered_copy(src,out,a,audit)
    assert result["page_order_changed"] is True
    with fitz.open(out) as doc: text=[p.get_text() for p in doc]
    assert "PAGE_BETA" in text[0] and "PAGE_GAMMA" in text[1] and "PAGE_ALPHA" in text[2]
    assert src.is_file()

def test_incomplete_folios_do_not_move_pages(tmp_path):
    src=tmp_path/"partial.pdf"; out=tmp_path/"copy.pdf"; a=tmp_path/"a.json"; audit=tmp_path/"out.json"
    make_pdf(src,[("PAGE_ALPHA",12),("PAGE_BETA",None),("PAGE_GAMMA",11)])
    data=analyze_pdf_order(src); assert data["recommendation"]=="MANUAL_REVIEW_REQUIRED"
    a.write_text(json.dumps(data),encoding="utf-8")
    result=create_safe_ordered_copy(src,out,a,audit)
    assert result["page_order_changed"] is False and result["status"]=="REVIEW_REQUIRED_NO_PAGES_MOVED"
    assert out.read_bytes()==src.read_bytes()

def test_academic_edition_has_outline_and_source_markers(tmp_path):
    src=tmp_path/"source.pdf"; out=tmp_path/"reader.pdf"; a=tmp_path/"analysis.json"; audit=tmp_path/"reader.audit.json"
    make_pdf(src,[("CAPÍTULO 1: Diagnóstico estructural\n\nTexto clínico de ejemplo.",10),("CAPÍTULO 2: La entrevista estructural\n\nSegundo bloque de texto.",11)])
    data=analyze_pdf_order(src); a.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
    result=create_academic_reading_edition(src,out,a,audit)
    assert result["status"]=="PASS_STRUCTURAL_CHECKS_HUMAN_REVIEW_REQUIRED"
    assert result["source_page_markers_verified"]==2 and result["chapter_and_part_navigation_entries"]==2
    with fitz.open(out) as doc:
        assert len(doc.get_toc())>=2
        text="\n".join(p.get_text() for p in doc)
    assert "Capítulo 1" in text and "Fuente PDF página 1" in text


def test_navigation_headings_exclude_attribution_and_body_text():
    from louksna_docworkbench.reading_edition import _heading_from_page, _trim_chapter_heading

    assert _heading_from_page(
        ["Capítulo 6: Adaptado de 'El tratamiento psicoterapéutico de las personalidades de la'"],
        toc_like=False,
    ) is None
    result = _heading_from_page(
        ["CAPÍTULO 2: La entrevista estructural Mi objetivo principal en este capítulo es ilustrar la"],
        toc_like=False,
    )
    assert result is not None
    assert result["title"] == "Capítulo 2: La entrevista estructural"
    assert result["source_line"] == result["title"]
    assert _trim_chapter_heading("Diagnóstico diferencial en la adolescencia Las consideraciones de") == "Diagnóstico diferencial en la adolescencia"
