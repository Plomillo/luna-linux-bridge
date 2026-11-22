from __future__ import annotations
import hashlib, json, pathlib, sys
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

docx_path = pathlib.Path(sys.argv[1])
evidence_path = pathlib.Path(sys.argv[2])
doc = Document(str(docx_path))

for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

for name in ("Normal", "Body Text"):
    if name in doc.styles:
        st = doc.styles[name]
        st.font.name = "Arial"
        st.font.size = Pt(12)
        st.paragraph_format.line_spacing = 1.5
        st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        st.paragraph_format.space_after = Pt(6)

for name in ("Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3"):
    if name in doc.styles:
        st = doc.styles[name]
        st.font.name = "Arial"
        st.font.size = Pt(12 if name == "Subtitle" else 16)
        if name != "Subtitle":
            st.font.bold = True
        st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        st.paragraph_format.line_spacing = 1.5
        st.paragraph_format.keep_with_next = True

page_break_heads = {
    "Introducción",
    "Desarrollo: 1. Atributos y expectativas asociados a cada género",
    "Desarrollo: 3. Influencia de los medios; 4. Conformidad y obediencia",
    "Referencias",
}
phase = "COVER"
for p in doc.paragraphs:
    txt = p.text.strip()
    if txt in page_break_heads:
        p.paragraph_format.page_break_before = True
        if txt == "Referencias":
            phase = "REFERENCES"
        else:
            phase = "BODY"
    if phase == "COVER":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif phase == "REFERENCES":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Cm(1.27)
        p.paragraph_format.first_line_indent = Cm(-1.27)
        p.paragraph_format.line_spacing = 1.5
    elif p.style.name.startswith("Heading"):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        if not p.paragraph_format.first_line_indent:
            p.paragraph_format.first_line_indent = Cm(1.25)
    for r in p.runs:
        r.font.name = "Arial"
        r.font.size = Pt(16 if p.style.name.startswith("Heading") or p.style.name == "Title" else 12)

doc.core_properties.title = "Comportamiento y género"
doc.core_properties.subject = "Ensayo académico — Unidad 1"
doc.core_properties.author = "Diego Ignacio Norabuena Miranda"
doc.save(str(docx_path))
sha = hashlib.sha256(docx_path.read_bytes()).hexdigest()
evidence_path.parent.mkdir(parents=True, exist_ok=True)
evidence_path.write_text(json.dumps({
  "schema":"UNIT1_DOCX_FORMATTING_EVIDENCE/1.0",
  "status":"APPLIED",
  "artifact":docx_path.name,
  "sha256":sha,
  "font":"Arial",
  "body_size_pt":12,
  "heading_size_pt":16,
  "line_spacing":1.5,
  "paragraph_alignment":"justified",
  "heading_alignment":"center",
  "margins_cm":{"top":2.5,"bottom":2.5,"left":2.5,"right":2.5},
  "body_page_breaks":sorted(page_break_heads),
  "rubric_detail_status":"OFFICIAL_RUBRIC_BREAKDOWN_NOT_PROVIDED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":"PASS","sha256":sha},sort_keys=True))
