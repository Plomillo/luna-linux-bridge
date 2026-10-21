from pathlib import Path

import fitz
import pytest

from louksna_docworkbench.engine import (
    _protect_glossary, inspect_pdf, normalize_extracted_text,
    parse_page_order, reflow_pdf, reorder_pdf,
)


def make_pdf(path: Path, pages: list[str]) -> None:
    document = fitz.open()
    for text in pages:
        page = document.new_page()
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_parse_page_order_requires_complete_permutation():
    assert parse_page_order("2,1,3", 3) == [1, 0, 2]
    with pytest.raises(ValueError):
        parse_page_order("2,1", 3)
    with pytest.raises(ValueError):
        parse_page_order("1,1,3", 3)
    with pytest.raises(ValueError):
        parse_page_order("1,2,4", 3)


def test_text_normalization_dehyphenates_and_joins_lines():
    assert normalize_extracted_text("transfe-\nrencia\n\nsegundo párrafo") == "transferencia\n\nsegundo párrafo"


def test_inspection_detects_pages_and_text(tmp_path):
    source = tmp_path / "source.pdf"
    make_pdf(source, ["Página uno con texto", "Página dos con texto"])
    result = inspect_pdf(source)
    assert result["page_count"] == 2
    assert result["input_sha256"]
    assert [page["page"] for page in result["pages"]] == [1, 2]


def test_reorder_creates_distinct_output(tmp_path):
    source = tmp_path / "source.pdf"
    output = tmp_path / "reordered.pdf"
    make_pdf(source, ["MARKER_FIRST", "MARKER_SECOND"])
    result = reorder_pdf(source, output, "2,1")
    assert result["verification"] == "PASS"
    with fitz.open(output) as doc:
        assert "MARKER_SECOND" in doc[0].get_text()
        assert "MARKER_FIRST" in doc[1].get_text()

def test_page_order_rejects_blank_items():
    with pytest.raises(ValueError):
        parse_page_order("1,,2", 2)
    with pytest.raises(ValueError):
        parse_page_order("", 2)


def test_glossary_protection_tracks_each_occurrence():
    protected, tokens, counts = _protect_glossary(
        "El apego y el apego seguro", {"apego": "attachment"}
    )
    assert len(tokens) == 2
    assert counts["apego"] == 2
    assert "attachment" not in protected
    assert all(token in protected for token in tokens)


def test_reflow_is_explicit_and_writes_audit(tmp_path):
    source = tmp_path / "source.pdf"
    output = tmp_path / "reading-copy.pdf"
    make_pdf(source, ["Este es un texto suficientemente largo para crear una copia de lectura."])
    with pytest.raises(ValueError):
        reflow_pdf(source, output, confirm_text_only=False)
    result = reflow_pdf(source, output, confirm_text_only=True)
    assert result["operation"] == "TEXT_ONLY_REFLOW"
    assert result["human_visual_review_required"] is True
    assert output.is_file()
    assert output.with_suffix(".pdf.audit.json").is_file()

