from __future__ import annotations
import hashlib,json,pathlib,sys
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches,Pt
docx_path=pathlib.Path(sys.argv[1]); evidence_path=pathlib.Path(sys.argv[2])
doc=Document(str(docx_path))
for s in doc.sections:
    s.top_margin=Inches(2.5/2.54); s.bottom_margin=Inches(2.5/2.54)
    s.left_margin=Inches(2.5/2.54); s.right_margin=Inches(2.5/2.54)
for name in ("Normal","Body Text"):
    if name in doc.styles:
        st=doc.styles[name]; st.font.name="Arial"; st.font.size=Pt(12)
        st.paragraph_format.line_spacing=1.5; st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
for name in ("Title","Heading 1","Heading 2","Heading 3"):
    if name in doc.styles:
        st=doc.styles[name]; st.font.name="Arial"; st.font.size=Pt(16); st.font.bold=True
        st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER; st.paragraph_format.line_spacing=1.5
        st.paragraph_format.keep_with_next=True
for p in doc.paragraphs:
    t=p.text.strip()
    if t=="Referencias":
        p.paragraph_format.page_break_before=True; p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    elif p.style.name.startswith("Heading"): p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    else:
        p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY; p.paragraph_format.line_spacing=1.5
    if t and p.style.name=="Normal": p.paragraph_format.space_after=Pt(5)
    for r in p.runs:
        r.font.name="Arial"
        r.font.size=Pt(16 if p.style.name.startswith("Heading") or p.style.name=="Title" else 12)
doc.core_properties.title="Examen final de Psicología"
doc.core_properties.author="Diego Ignacio Norambuena Miranda"
doc.core_properties.subject="Evaluación final — Psicología"
doc.save(str(docx_path))
evidence_path.parent.mkdir(parents=True,exist_ok=True)
evidence_path.write_text(json.dumps({"schema":"PSICOLOGIA_U4_FORMATTING_EVIDENCE/1.0","status":"APPLIED",
 "artifact":docx_path.name,"sha256":hashlib.sha256(docx_path.read_bytes()).hexdigest(),
 "font":"Arial","body_size_pt":12,"heading_size_pt":16,"line_spacing":1.5,
 "paragraph_alignment":"justified","margins_cm":2.5,"references_page_break":True},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
