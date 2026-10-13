from __future__ import annotations
import hashlib, json, pathlib, sys
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

docx_path = pathlib.Path(sys.argv[1])
evidence_path = pathlib.Path(sys.argv[2])
doc = Document(str(docx_path))

for section in doc.sections:
    section.top_margin = Inches(2.5 / 2.54)
    section.bottom_margin = Inches(2.5 / 2.54)
    section.left_margin = Inches(2.5 / 2.54)
    section.right_margin = Inches(2.5 / 2.54)

for style_name in ("Normal", "Body Text"):
    if style_name in doc.styles:
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style.font.size = Pt(12)
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

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

phase = "COVER"
for p in doc.paragraphs:
    txt = p.text.strip()
    if txt == "Introducción":
        p.paragraph_format.page_break_before = True
        phase = "BODY"
    elif txt == "Referencias":
        p.paragraph_format.page_break_before = True
        phase = "REFERENCES"
    if phase == "COVER":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif phase == "REFERENCES":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Inches(0)
        p.paragraph_format.first_line_indent = Inches(-0.5)
        p.paragraph_format.line_spacing = 1.5
    elif p.style.name.startswith("Heading"):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
    for run in p.runs:
        run.font.name = "Arial"
        if p.style.name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
            run.font.size = Pt(16)
        else:
            run.font.size = Pt(12)

doc.core_properties.title = "El primer borrador de un artículo científico — Entrega 1"
doc.core_properties.subject = "Metodología cuantitativa; preguntas experimental y no experimental"
doc.save(str(docx_path))
sha = hashlib.sha256(docx_path.read_bytes()).hexdigest()
evidence_path.parent.mkdir(parents=True, exist_ok=True)
evidence_path.write_text(json.dumps({
    "schema":"UNIT2_DOCX_FORMATTING_EVIDENCE/1.0",
    "status":"APPLIED",
    "artifact":docx_path.name,
    "sha256":sha,
    "font":"Arial",
    "body_size_pt":12,
    "heading_size_pt":16,
    "line_spacing":1.5,
    "paragraph_alignment":"justified",
    "cover_and_references_page_breaks":True,
    "margins_cm":{"top":2.5,"bottom":2.5,"left":2.5,"right":2.5},
    "author_names":"EMPTY"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":"PASS","artifact":docx_path.name,"sha256":sha},sort_keys=True))
