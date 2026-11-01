from __future__ import annotations
import hashlib,json,pathlib,sys
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches,Pt
path=pathlib.Path(sys.argv[1]); evidence=pathlib.Path(sys.argv[2]); doc=Document(str(path))
for s in doc.sections:
    s.page_width=Inches(8.5); s.page_height=Inches(11)
    s.top_margin=Inches(2.5/2.54); s.bottom_margin=Inches(2.5/2.54)
    s.left_margin=Inches(2.5/2.54); s.right_margin=Inches(2.5/2.54)
for name in ("Normal","Body Text"):
    if name in doc.styles:
        st=doc.styles[name]; st.font.name="Arial"; st.font.size=Pt(12)
        st.paragraph_format.line_spacing=1.5; st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        st.paragraph_format.space_after=Pt(4)
for name in ("Title","Heading 1","Heading 2","Heading 3"):
    if name in doc.styles:
        st=doc.styles[name]; st.font.name="Arial"; st.font.size=Pt(16); st.font.bold=True
        st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER; st.paragraph_format.line_spacing=1.5
        st.paragraph_format.keep_with_next=True
for p in doc.paragraphs:
    if p.style.name.startswith("Heading"): p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    else:
        p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY; p.paragraph_format.line_spacing=1.5
    for r in p.runs:
        r.font.name="Arial"; r.font.size=Pt(16 if p.style.name.startswith("Heading") or p.style.name=="Title" else 12)
for table in doc.tables:
    table.autofit=True
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing=1.5
                for r in p.runs: r.font.name="Arial"; r.font.size=Pt(12)
doc.core_properties.title="Estudiar en compañía a distancia: Study With Me y comunicación digital"
doc.core_properties.author="Diego Ignacio Norambuena Miranda"
doc.core_properties.subject="Proyecto integrador de Comunicación — Unidad 4"
doc.save(str(path))
evidence.parent.mkdir(parents=True,exist_ok=True)
evidence.write_text(json.dumps({"schema":"COMUNICACION_U4_FORMATTING_EVIDENCE/1.0","status":"APPLIED",
"artifact":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"font":"Arial",
"body_size_pt":12,"heading_size_pt":16,"table_text_size_pt":12,"line_spacing":1.5,
"paper":"Letter","margins_cm":2.5,"paragraph_alignment":"justified"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
