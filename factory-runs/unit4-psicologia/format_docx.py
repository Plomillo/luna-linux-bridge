from __future__ import annotations
import hashlib,json,pathlib,sys
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches,Pt,RGBColor

docx_path=pathlib.Path(sys.argv[1]); evidence_path=pathlib.Path(sys.argv[2])
doc=Document(str(docx_path))
for s in doc.sections:
    s.page_width=Inches(8.5); s.page_height=Inches(11)
    s.top_margin=Inches(2.5/2.54); s.bottom_margin=Inches(2.5/2.54)
    s.left_margin=Inches(2.5/2.54); s.right_margin=Inches(2.5/2.54)
    header=s.header.paragraphs[0]; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    run=header.add_run(); fld=OxmlElement("w:fldSimple"); fld.set(qn("w:instr"),"PAGE"); run._r.addnext(fld)
for name in ("Normal","Body Text"):
    if name in doc.styles:
        st=doc.styles[name]; st.font.name="Arial"; st.font.size=Pt(12)
        st.paragraph_format.line_spacing=1.5; st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        st.paragraph_format.space_after=Pt(0)
for name in ("Title","Heading 1","Heading 2","Heading 3"):
    if name in doc.styles:
        st=doc.styles[name]; st.font.name="Arial"; st.font.size=Pt(16); st.font.bold=True; st.font.color.rgb=RGBColor(0,0,0)
        st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER; st.paragraph_format.line_spacing=1.5
        st.paragraph_format.keep_with_next=True; st.paragraph_format.space_before=Pt(0); st.paragraph_format.space_after=Pt(0)
in_refs=False
for p in doc.paragraphs:
    t=p.text.strip()
    if t=="Referencias": in_refs=True
    if p.style.name.startswith("Heading"):
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    elif t.startswith(("Asignatura:","Docente:","Estudiante:")):
        p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing=1.5
    elif in_refs and t:
        p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing=1.5
        p.paragraph_format.left_indent=Inches(0.5)
        p.paragraph_format.first_line_indent=Inches(-0.5)
    else:
        p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing=1.5
        p.paragraph_format.space_after=Pt(0)
    for r in p.runs:
        r.font.name="Arial"; r.font.size=Pt(16 if p.style.name.startswith("Heading") or p.style.name=="Title" else 12)
        if p.style.name.startswith("Heading"): r.font.color.rgb=RGBColor(0,0,0)
doc.core_properties.title="Examen final — Introducción a la Psicología"
doc.core_properties.author="Diego Ignacio Norambuena Miranda"
doc.core_properties.subject="Introducción a la Psicología — Unidad 4"
doc.save(str(docx_path))
evidence_path.parent.mkdir(parents=True,exist_ok=True)
evidence_path.write_text(json.dumps({"schema":"PSICOLOGIA_U4_FORMATTING_EVIDENCE/1.0","status":"APPLIED",
"artifact":docx_path.name,"sha256":hashlib.sha256(docx_path.read_bytes()).hexdigest(),
"font":"Arial","body_size_pt":12,"all_heading_size_pt":16,"line_spacing":1.5,
"body_alignment":"justified","metadata_alignment":"left","references_alignment":"left",
"margins_cm":2.5,"references_hanging_indent":True,"page_numbers":True,"references_page_break":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
