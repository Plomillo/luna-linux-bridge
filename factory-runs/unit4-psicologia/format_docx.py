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

# Minimalist UNIACC cover header — integrated on page one, without an extra page.
cover_logo = pathlib.Path(__file__).resolve().parents[1] / "unit2-epistemologia" / "assets" / "LOGO_UNIACC.png"
if not cover_logo.is_file():
    raise FileNotFoundError(f"UNIACC_LOGO_NOT_FOUND:{cover_logo}")
cover_paragraphs = [p for p in doc.paragraphs if p.text.strip()]
if not cover_paragraphs:
    raise ValueError("COVER_TITLE_NOT_FOUND")
logo_paragraph = cover_paragraphs[0].insert_paragraph_before()
logo_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
logo_paragraph.paragraph_format.space_before = Pt(0)
logo_paragraph.paragraph_format.space_after = Pt(3)
logo_paragraph.paragraph_format.line_spacing = 1.0
logo_paragraph.add_run().add_picture(str(cover_logo), height=Inches(0.38))
for index, paragraph in enumerate(cover_paragraphs[:2]):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(1)
    paragraph.paragraph_format.space_after = Pt(2 if index == 0 else 4)
    for run in paragraph.runs:
        run.font.name = "Arial"
        run.font.size = Pt(16 if paragraph.style.name.startswith("Heading") or paragraph.style.name == "Title" else 12)
        run.font.bold = True
# Add only bibliographic cover metadata already established by the assignment record.
required_cover_metadata = [
    "Asignatura: INTRODUCCIÓN A LA PSICOLOGÍA — 387",
    "Docente: Nicole Elena Castro Valenzuela",
    "Estudiante: Diego Ignacio Norambuena Miranda",
]
existing_fields = {p.text.strip().split(":", 1)[0].casefold() for p in doc.paragraphs if ":" in p.text}
anchor = next((p for p in doc.paragraphs if p.text.strip().startswith("Caso de estudio:")), None)
if anchor is None:
    raise ValueError("CASE_HEADING_NOT_FOUND_FOR_COVER_METADATA")
for line in required_cover_metadata:
    field = line.split(":", 1)[0].casefold()
    if field not in existing_fields:
        anchor.insert_paragraph_before(line)
cover_metadata = [p for p in doc.paragraphs if p.text.strip().startswith(("Asignatura:", "Docente:", "Estudiante:"))]
for paragraph in cover_metadata:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(1)
    for run in paragraph.runs:
        run.font.name = "Arial"
        run.font.size = Pt(9)
# A restrained UNIACC-red rule closes the title block without changing report text.
if cover_metadata:
    ppr = cover_metadata[-1]._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), "A6192E")
    borders.append(bottom)
    ppr.append(borders)

doc.save(str(docx_path))
evidence_path.parent.mkdir(parents=True,exist_ok=True)
evidence_path.write_text(json.dumps({"schema":"PSICOLOGIA_U4_FORMATTING_EVIDENCE/1.0","status":"APPLIED",
"artifact":docx_path.name,"sha256":hashlib.sha256(docx_path.read_bytes()).hexdigest(),
"font":"Arial","body_size_pt":12,"all_heading_size_pt":16,"line_spacing":1.5,
"body_alignment":"justified","metadata_alignment":"left","references_alignment":"left",
"margins_cm":2.5,"references_hanging_indent":True,"page_numbers":True,"references_page_break":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
