#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, sys
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

if len(sys.argv) != 4:
    raise SystemExit("usage: format_docx.py report.docx evidence.json ENTREGA3|ENTREGA4")

docx_path = pathlib.Path(sys.argv[1])
evidence_path = pathlib.Path(sys.argv[2])
profile_kind = sys.argv[3]
if profile_kind not in {"ENTREGA3", "ENTREGA4"}:
    raise SystemExit("UNKNOWN_PROFILE_KIND")

doc = Document(str(docx_path))
for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.page_width = Cm(21.59)
    section.page_height = Cm(27.94)

for style_name in ("Normal", "Body Text"):
    if style_name in doc.styles:
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style.font.size = Pt(12)
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        style.paragraph_format.space_after = Pt(3)

for style_name in ("Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3"):
    if style_name in doc.styles:
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style.font.size = Pt(16 if style_name != "Subtitle" else 12)
        if style_name != "Subtitle":
            style.font.bold = True
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(6)
        style.paragraph_format.space_after = Pt(4)

references_seen = False
for paragraph in doc.paragraphs:
    text = paragraph.text.strip()
    if text.lower() == "referencias":
        references_seen = True
    if paragraph.style.name.startswith("Heading"):
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.keep_with_next = True
    elif references_seen:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.left_indent = Cm(1.27)
        paragraph.paragraph_format.first_line_indent = Cm(-1.27)
        paragraph.paragraph_format.line_spacing = 1.5
    else:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.line_spacing = 1.5
    for run in paragraph.runs:
        run.font.name = "Arial"
        if paragraph.style.name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
            run.font.size = Pt(16)
        else:
            run.font.size = Pt(12)

for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.line_spacing = 1.0
                for run in paragraph.runs:
                    run.font.name = "Arial"
                    run.font.size = Pt(9)

doc.core_properties.author = "Valeria Galaz; Diego Norambuena; Paula Pizarro; Joel Quezada"
doc.core_properties.subject = "Metodología cuantitativa — investigación sobre planificación y atención selectiva"
doc.save(str(docx_path))

digest = hashlib.sha256(docx_path.read_bytes()).hexdigest()
evidence_path.parent.mkdir(parents=True, exist_ok=True)
evidence_path.write_text(json.dumps({
    "schema": "UNIACC_QUANTITATIVE_REPORT_FORMAT/1.0",
    "status": "APPLIED",
    "artifact": docx_path.name,
    "sha256": digest,
    "profile_kind": profile_kind,
    "font": "Arial",
    "body_size_pt": 12,
    "heading_size_pt": 16,
    "line_spacing": 1.5,
    "paragraph_alignment": "justified",
    "references_hanging_indent": True,
    "margins_cm": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
    "page_size": "Letter",
    "cover_page_inserted": False,
    "g23_authority": False,
    "g24_authority": False
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "PASS", "artifact": docx_path.name, "sha256": digest}, sort_keys=True))
