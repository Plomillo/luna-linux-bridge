from __future__ import annotations
import json,pathlib,re,subprocess,sys
from docx import Document
root=pathlib.Path(sys.argv[1]); profile=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
docx=root/"build/report.docx"; pdf=root/"build/report.pdf"; md=root/"source/report.md"
assert docx.is_file() and pdf.is_file() and pdf.stat().st_size>0
info=subprocess.run(["pdfinfo",str(pdf)],capture_output=True,text=True,check=True).stdout
m=re.search(r"^Pages:\s+(\d+)\s*$",info,re.M); assert m,"PDF_PAGE_COUNT_UNREADABLE"
pages=int(m.group(1)); assert 3<=pages<=5,f"PAGE_COUNT_OUT_OF_RANGE:{pages}"
text=subprocess.run(["pdftotext","-layout",str(pdf),"-"],capture_output=True,text=True,check=True).stdout
flat=" ".join(text.casefold().split())
for required in ["Caso de estudio","1. Aproximación filosófica","2. Aproximación teórica","3. Dilemas éticos","4. Interacción de los campos","5. Métodos y estrategias","6. Reflexión sobre la práctica","Referencias"]:
    assert required.casefold() in flat,"MISSING_SECTION:"+required
raw=md.read_text(encoding="utf-8")
case=re.search(r"## Caso de estudio:[^\n]*\n(.*?)\n\*\*Datos clave",raw,re.S)
assert case,"CASE_BLOCK_MISSING"
words=re.findall(r"\b[\wÀ-ÿ'-]+\b",case.group(1),re.UNICODE)
assert 300<=len(words)<=400,f"CASE_LENGTH:{len(words)}"
for q in range(1,7): assert f"### {q}." in raw,f"QUESTION_{q}_MISSING"
for marker in ["positivismo","Wundt","1879","funcionalismo","psicoanálisis","condicionamiento","Rogers","Piaget","Vygotsky","Erikson","confidencialidad","autonomía progresiva","social-comunitaria","adaptación cultural"]:
    assert marker.casefold() in raw.casefold(),"RUBRIC_CONTENT_MISSING:"+marker
order=["Biblioteca del Congreso Nacional de Chile.","Colegio de Psicólogos de Chile.","Cosacov,","Danziger,","Erikson,","Freud,","Piaget,","Rogers,","Sáiz,","Skinner,","Universidad UNIACC. (s. f.)","Universidad UNIACC. (2025)","Vygotsky,"]
positions=[raw.index(x,raw.index("## Referencias")) for x in order]
assert positions==sorted(positions),"APA_REFERENCE_ORDER_FAIL"
assert "[completar]" in raw and "Caso deliberadamente ficticio" in raw
d=Document(str(docx)); sec=d.sections[0]
for value in [sec.top_margin,sec.bottom_margin,sec.left_margin,sec.right_margin]:
    assert abs(value.inches*2.54-2.5)<0.03,"MARGIN_FAIL"
assert d.styles["Normal"].font.name=="Arial" and abs(d.styles["Normal"].font.size.pt-12)<0.01
for name in ("Title","Heading 1","Heading 2","Heading 3"):
    if name in d.styles:
        st=d.styles[name]
        assert st.font.name=="Arial" and st.font.size is not None and abs(st.font.size.pt-16)<0.01,f"HEADING_STYLE_FAIL:{name}"
for p in d.paragraphs:
    if p.style.name.startswith("Heading"):
        for run in p.runs:
            if run.text.strip():
                assert run.font.size is not None and abs(run.font.size.pt-16)<0.01,"HEADING_RUN_NOT_16PT"
missing=json.loads((root/"data/missing-inputs.json").read_text(encoding="utf-8"))
assert missing["status"]=="PARTIAL_SOURCE_COMPLETENESS"
assert missing["blocking_or_material_gaps"],"INPUT_GAPS_NOT_DOCUMENTED"
result={"schema":"PSICOLOGIA_U4_DELIVERABLE_VERIFICATION/1.0","status":"PASS_WITH_DOCUMENTED_INPUT_GAPS",
"pdf_pages":pages,"pdf_bytes":pdf.stat().st_size,"case_words":len(words),"six_development_answers_present":True,
"heading_size_pt":16,"body_size_pt":12,"references_alphabetical":True,
"rubric_total":profile["rubric"]["declared_total_points"],"multiple_choice_12":"NOT_ANSWERED_SOURCE_MISSING",
"personal_context":"PLACEHOLDER_PENDING_USER_DATA","g23":"NOT_EXECUTED","g24":"NOT_EXECUTED"}
(root/"evidence").mkdir(exist_ok=True)
(root/"evidence/document-verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
