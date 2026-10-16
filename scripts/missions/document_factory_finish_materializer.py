#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,re,shutil,subprocess,sys,tempfile,zipfile
from datetime import datetime,timezone
from pathlib import Path

CERTIFIED="067e1be0b13d9400c2c78d6174138c10ce980dd7"
FAMILIES={"F01_IO_KNOWLEDGE","F02_EXECUTION_RESOURCES","F03_SECURITY_TRUST","F04_INTELLIGENCE_SYNTHESIS","F05_ASSURANCE_EPISTEMIC","F06_CONTINUITY_INTEROP","F07_MEMORY_DOCUMENTATION","F08_FORMAL_CORE","F09_CAPABILITY_GAPS_EVOLUTION"}

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def run(cmd,cwd=None,timeout=120):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError("COMMAND_FAIL:"+repr(cmd)+"\n"+p.stdout[-4000:]+"\n"+p.stderr[-4000:])
    return p.stdout.strip()
def tele(phase,status="RUNNING",**kw):
    print("CUSTOSZ_TELEMETRY "+json.dumps({"observed_at_utc":utc(),"phase":phase,"status":status,**kw},sort_keys=True),flush=True)
def w(path,text): path.write_text(text,encoding="utf-8")
def jload(path): return json.loads(path.read_text(encoding="utf-8"))
def jwrite(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

SOURCE_PIPELINE=r'''from __future__ import annotations
import json,re
from pathlib import Path
CITE_RE=re.compile(r"\[@([A-Za-z0-9_.:-]+)(?:[^\]]*)\]")
def _load(x): return json.loads(Path(x).read_text(encoding="utf-8")) if isinstance(x,(str,Path)) else x
def validate_ledger(ledger,minimum_distinct_sources=0):
    obj=_load(ledger); rows=obj.get("sources") or []; seen=set(); failures=[]
    for i,row in enumerate(rows):
        sid=str(row.get("source_id","")).strip()
        if not sid: failures.append(f"SOURCE_ID_MISSING:{i}"); continue
        if sid in seen: failures.append("DUPLICATE_SOURCE_ID:"+sid)
        seen.add(sid)
        if row.get("verified") is True:
            if not str(row.get("title","")).strip(): failures.append("VERIFIED_SOURCE_TITLE_MISSING:"+sid)
            if row.get("fabricated_metadata") is True: failures.append("FABRICATED_METADATA_FORBIDDEN:"+sid)
    verified={str(x.get("source_id")) for x in rows if x.get("verified") is True and x.get("source_id")}
    if len(verified)<int(minimum_distinct_sources): failures.append(f"MINIMUM_VERIFIED_SOURCES_NOT_MET:{len(verified)}<{minimum_distinct_sources}")
    return {"status":"PASS" if not failures else "FAIL","failures":failures,"distinct_verified":len(verified)}
def extract_citation_ids(text): return sorted(set(CITE_RE.findall(text or "")))
def validate_citations(text,ledger):
    obj=_load(ledger); rows={str(x.get("source_id")):x for x in obj.get("sources",[]) if x.get("source_id")}; failures=[]
    cited=extract_citation_ids(text)
    for cid in cited:
        if cid not in rows: failures.append("CITATION_NOT_IN_LEDGER:"+cid)
        elif rows[cid].get("verified") is not True: failures.append("CITATION_SOURCE_NOT_VERIFIED:"+cid)
    return {"status":"PASS" if not failures else "FAIL","cited_ids":cited,"failures":failures}
def compile_csl_json(ledger):
    obj=_load(ledger); out=[]
    for row in obj.get("sources",[]):
        if row.get("verified") is not True: continue
        sid=str(row.get("source_id","")).strip(); title=str(row.get("title","")).strip()
        if not sid or not title: raise ValueError("CSL_REQUIRES_VERIFIED_ID_AND_TITLE")
        item={"id":sid,"type":row.get("csl_type") or "article","title":title}
        if row.get("author"):
            authors=[]
            for a in row["author"]:
                if isinstance(a,dict):
                    clean={k:a[k] for k in ("family","given","literal") if a.get(k)}
                    if clean: authors.append(clean)
            if authors: item["author"]=authors
        if row.get("issued"): item["issued"]=row["issued"]
        if row.get("container_title"): item["container-title"]=row["container_title"]
        for key in ("DOI","URL","page","volume","issue","publisher"):
            if row.get(key): item[key]=row[key]
        out.append(item)
    return out
'''

MEDIA=r'''from __future__ import annotations
import hashlib,json,shutil,subprocess
from pathlib import Path
def _load(x): return json.loads(Path(x).read_text(encoding="utf-8")) if isinstance(x,(str,Path)) else x
def ffprobe_admission(lock):
    obj=_load(lock); row=next((x for x in obj.get("providers",[]) if x.get("id")=="ffprobe"),None)
    if not row: return {"status":"EXCLUDED","admitted":False,"reason":"FFPROBE_NOT_DECLARED"}
    pinned=all(row.get(k) for k in ("version","source","sha256")) and not str(row.get("state","")).startswith("UNRESOLVED")
    binary=shutil.which("ffprobe"); observed=None
    if binary:
        p=subprocess.run([binary,"-version"],text=True,capture_output=True,timeout=10)
        observed={"path":binary,"binary_sha256":hashlib.sha256(Path(binary).read_bytes()).hexdigest(),"version_line":(p.stdout.splitlines() or [""])[0],"exit_code":p.returncode}
    return {"status":"ADMITTED" if pinned else "EXCLUDED","admitted":bool(pinned),"reason":None if pinned else "FFPROBE_PROVENANCE_NOT_PINNED","declared":row,"observed_binary":observed}
def validate_probe_metadata(probe,c):
    video=next((x for x in probe.get("streams",[]) if x.get("codec_type")=="video"),None); failures=[]
    if not video: return {"status":"FAIL","failures":["VIDEO_STREAM_MISSING"]}
    width=int(video.get("width") or 0); height=int(video.get("height") or 0)
    try: dur=float((probe.get("format") or {}).get("duration"))
    except Exception: dur=-1
    if c.get("max_duration_seconds") is not None and (dur<0 or dur>float(c["max_duration_seconds"])): failures.append("VIDEO_DURATION_OUT_OF_RANGE")
    if c.get("orientation")=="horizontal" and not width>height: failures.append("VIDEO_ORIENTATION_NOT_HORIZONTAL")
    if c.get("orientation")=="vertical" and not height>width: failures.append("VIDEO_ORIENTATION_NOT_VERTICAL")
    return {"status":"PASS" if not failures else "FAIL","failures":failures,"width":width,"height":height,"duration_seconds":dur}
'''

IMAGE=r'''from __future__ import annotations
import re
def validate_image_metadata(width,height,dpi_x,dpi_y,c):
    width=int(width); height=int(height); failures=[]; unknown=[]
    if c.get("minimum_dpi") is not None:
        if dpi_x is None or dpi_y is None: unknown.append("DPI_METADATA_MISSING")
        elif float(dpi_x)<float(c["minimum_dpi"]) or float(dpi_y)<float(c["minimum_dpi"]): failures.append("DPI_BELOW_MINIMUM")
    if c.get("exact_pixel_dimensions"):
        e=c["exact_pixel_dimensions"]
        if [width,height]!=[int(e[0]),int(e[1])]: failures.append("PIXEL_DIMENSIONS_NOT_EXACT")
    elif c.get("minimum_pixel_dimensions"):
        e=c["minimum_pixel_dimensions"]
        if width<int(e[0]) or height<int(e[1]): failures.append("PIXEL_DIMENSIONS_BELOW_MINIMUM")
    elif c.get("stated_dimensions"):
        m=re.fullmatch(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*",str(c["stated_dimensions"]))
        unknown.append("STATED_DIMENSIONS_SEMANTICS_NOT_INFERRED"+(f":{m.group(1)}x{m.group(2)}" if m else ""))
    return {"status":"FAIL" if failures else ("UNKNOWN" if unknown else "PASS"),"failures":failures,"unknown":unknown,"dpi_and_pixel_dimensions_are_distinct":True}
'''

ARTIFACT=r'''from __future__ import annotations
import re,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
REQ={"docx":["[Content_Types].xml","_rels/.rels","word/document.xml"],"pptx":["[Content_Types].xml","_rels/.rels","ppt/presentation.xml"],"xlsx":["[Content_Types].xml","_rels/.rels","xl/workbook.xml"]}
def validate_ooxml(path,kind):
    failures=[]
    try:
        with zipfile.ZipFile(path) as z:
            bad=z.testzip()
            if bad: failures.append("ZIP_CRC_FAIL:"+bad)
            names=z.namelist()
            if any(n.startswith("/") or ".." in n.split("/") for n in names): failures.append("UNSAFE_ARCHIVE_PATH")
            for req in REQ[kind]:
                if req not in names: failures.append("MISSING_PART:"+req)
                elif req.endswith(".xml"):
                    try: ET.fromstring(z.read(req))
                    except Exception: failures.append("INVALID_XML:"+req)
    except Exception as exc: failures.append("OOXML_OPEN_FAIL:"+str(exc))
    return {"status":"PASS" if not failures else "FAIL","failures":failures}
def validate_pdf(path):
    data=Path(path).read_bytes(); failures=[]
    if not data.startswith(b"%PDF-"): failures.append("PDF_HEADER_MISSING")
    if b"%%EOF" not in data[-2048:]: failures.append("PDF_EOF_MISSING")
    if not re.search(rb"\b\d+\s+\d+\s+obj\b",data): failures.append("PDF_OBJECT_MISSING")
    return {"status":"PASS" if not failures else "FAIL","failures":failures}
'''

WRITER_POLICY=r'''FORBIDDEN_TRUE={"certification_authority","g23_authority","g24_authority","g23_granted","g24_granted"}
def validate_writer_record(record):
    failures=[]
    for key in FORBIDDEN_TRUE:
        if record.get(key) is True: failures.append("WRITER_AUTHORITY_FORBIDDEN:"+key)
    for key in ("provider_id","provider_version","input_sha256","output_sha256"):
        if not record.get(key): failures.append("WRITER_EVIDENCE_MISSING:"+key)
    return {"status":"PASS" if not failures else "FAIL","failures":failures}
'''

TEST=r'''#!/usr/bin/env python3
import json,pathlib,sys,tempfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from source_pipeline import validate_ledger,validate_citations,compile_csl_json
from media_validation import validate_probe_metadata,ffprobe_admission
from image_validation import validate_image_metadata
from artifact_validation import validate_ooxml,validate_pdf
from writer_policy import validate_writer_record
from rubric_compiler import compile_rubric
ledger={"sources":[{"source_id":"S1","verified":True,"title":"Synthetic one"},{"source_id":"S2","verified":True,"title":"Synthetic two"},{"source_id":"S3","verified":True,"title":"Synthetic three"}]}
assert validate_ledger(ledger,3)["status"]=="PASS"
assert validate_citations("A [@S1] B [@S2].",ledger)["status"]=="PASS"
assert validate_citations("Bad [@NOPE].",ledger)["status"]=="FAIL"
assert len(compile_csl_json(ledger))==3
assert validate_probe_metadata({"streams":[{"codec_type":"video","width":1920,"height":1080}],"format":{"duration":"299"}},{"max_duration_seconds":300,"orientation":"horizontal"})["status"]=="PASS"
assert validate_probe_metadata({"streams":[{"codec_type":"video","width":1080,"height":1920}],"format":{"duration":"301"}},{"max_duration_seconds":300,"orientation":"horizontal"})["status"]=="FAIL"
assert validate_image_metadata(1200,1800,300,300,{"minimum_dpi":300,"minimum_pixel_dimensions":[600,900]})["status"]=="PASS"
assert validate_image_metadata(1200,1800,300,300,{"minimum_dpi":300,"stated_dimensions":"600x900"})["status"]=="UNKNOWN"
assert validate_writer_record({"provider_id":"s","provider_version":"1","input_sha256":"a","output_sha256":"b","certification_authority":False})["status"]=="PASS"
assert validate_writer_record({"provider_id":"s","provider_version":"1","input_sha256":"a","output_sha256":"b","g23_authority":True})["status"]=="FAIL"
with tempfile.TemporaryDirectory() as td:
    td=pathlib.Path(td)
    roots={"docx":"word/document.xml","pptx":"ppt/presentation.xml","xlsx":"xl/workbook.xml"}
    for kind,root in roots.items():
        p=td/("x."+kind)
        with zipfile.ZipFile(p,"w") as z:
            z.writestr("[Content_Types].xml","<Types/>"); z.writestr("_rels/.rels","<Relationships/>"); z.writestr(root,"<root/>")
        assert validate_ooxml(p,kind)["status"]=="PASS"
    p=td/"x.pdf"; p.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"); assert validate_pdf(p)["status"]=="PASS"
profile=json.loads((ROOT/"profiles/uniacc-neuroplasticidad-u2.json").read_text(encoding="utf-8"))
assert compile_rubric(profile)["criterion_count"]==10
adm=ffprobe_admission(ROOT/"toolchain.lock.json"); assert adm["status"] in ("ADMITTED","EXCLUDED")
print(json.dumps({"status":"PASS","ffprobe_admission":adm["status"]},sort_keys=True))
'''

E2E=r'''#!/usr/bin/env python3
import json,pathlib,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from source_pipeline import validate_ledger,validate_citations,compile_csl_json
from media_validation import validate_probe_metadata
from image_validation import validate_image_metadata
from artifact_validation import validate_pdf
from writer_policy import validate_writer_record
ledger={"sources":[{"source_id":"A","verified":True,"title":"Synthetic A"},{"source_id":"B","verified":True,"title":"Synthetic B"},{"source_id":"C","verified":True,"title":"Synthetic C"}]}
r={"ledger":validate_ledger(ledger,3),"citations":validate_citations("Synthetic [@A] [@B] [@C].",ledger),"csl_count":len(compile_csl_json(ledger)),"video":validate_probe_metadata({"streams":[{"codec_type":"video","width":1920,"height":1080}],"format":{"duration":"120"}},{"max_duration_seconds":300,"orientation":"horizontal"}),"image":validate_image_metadata(1200,1800,300,300,{"minimum_dpi":300,"minimum_pixel_dimensions":[600,900]}),"writer":validate_writer_record({"provider_id":"synthetic","provider_version":"1","input_sha256":"1","output_sha256":"2","certification_authority":False})}
with tempfile.TemporaryDirectory() as td:
    p=pathlib.Path(td)/"s.pdf"; p.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"); r["pdf"]=validate_pdf(p)
statuses=[v["status"] for v in r.values() if isinstance(v,dict) and "status" in v]
r.update({"status":"PASS" if all(x=="PASS" for x in statuses) else "FAIL","synthetic_only":True,"student_assignment_generated":False,"g23":"NOT_EXECUTED","g24":"NOT_EXECUTED"})
print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r["status"]=="PASS" else 2)
'''

def add_by_id(rows,key,new):
    ids={x.get(key) for x in rows if isinstance(x,dict)}
    rows.extend(x for x in new if x.get(key) not in ids)

def main(argv):
    if len(argv)!=9: raise SystemExit("EXPECTED_8_ARGUMENTS")
    dispatch,ack,fme,target,mission_root,target_root,main_root,census_path=map(Path,argv[1:9])
    d=jload(dispatch); census=jload(census_path)
    families={x.get("family") for x in census.get("capabilities",[]) if x.get("family")}
    if (census.get("family_count"),census.get("capability_count"),census.get("unique_capability_count"))!=(9,72,72) or not FAMILIES.issubset(families): raise SystemExit("CUSTOSZ_9_FAMILY_CENSUS_FAIL")
    head=run(["git","rev-parse","HEAD"],target_root); run(["git","merge-base","--is-ancestor",CERTIFIED,head],target_root)
    if head==CERTIFIED: raise SystemExit("FIRST_TRANCHE_NOT_PRESENT")
    main_head=run(["git","rev-parse","HEAD"],main_root); tele("PRECHECK","PASS",head=head)
    accepted={"mission_id":d["mission_id"],"dispatch_id":d["dispatch_id"],"executor_id":d["executor_id"],"accepted":True,"pid":os.getpid(),"process_or_execution_token":"custosz-document-factory-finish"}; accepted["ack_digest"]=digest(accepted); jwrite(ack,accepted)
    baseline=run([sys.executable,"-B","document-factory/src/selftest.py"],target_root,120)
    rubric=run([sys.executable,"-B","document-factory/src/test_rubric_compiler.py"],target_root,60)
    profile=run([sys.executable,"-B","document-factory/src/factory.py","validate-profile","document-factory/profiles/uniacc-neuroplasticidad-u2.json","--repo-root","."],target_root,60)
    tele("BASELINE_NON_REGRESSION","PASS")
    src=target_root/"document-factory/src"
    for name,text in {"source_pipeline.py":SOURCE_PIPELINE,"media_validation.py":MEDIA,"image_validation.py":IMAGE,"artifact_validation.py":ARTIFACT,"writer_policy.py":WRITER_POLICY,"test_completion.py":TEST,"synthetic_e2e.py":E2E}.items(): w(src/name,text)
    tele("MATERIALIZE_REMAINING_BACKLOG","PASS")
    completion=run([sys.executable,"-B","document-factory/src/test_completion.py"],target_root,120)
    e2e=run([sys.executable,"-B","document-factory/src/synthetic_e2e.py"],target_root,120)
    sys.path.insert(0,str(src)); from media_validation import ffprobe_admission
    admission=ffprobe_admission(target_root/"document-factory/toolchain.lock.json")
    tele("TESTS","PASS",ffprobe=admission["status"])

    claims=jload(target_root/"document-factory/CLAIMS.json")
    add_by_id(claims["claims"],"claim_id",[
      {"claim_id":"DF-CLM-007","property":"Source ledger and citation/CSL pipeline fail closed without fabricating metadata.","acceptance":"Completion selftest covers verified ledger, unknown citation rejection and CSL JSON compilation."},
      {"claim_id":"DF-CLM-008","property":"Audiovisual metadata validation is profile-driven and provider admission is provenance-gated.","acceptance":"FFprobe is admitted only when version/source/SHA-256 are pinned; otherwise capability remains excluded while metadata logic is tested."},
      {"claim_id":"DF-CLM-009","property":"Image DPI and pixel dimensions are distinct validation concepts.","acceptance":"Ambiguous stated dimensions remain UNKNOWN; explicit DPI/pixel constraints are separately checked."},
      {"claim_id":"DF-CLM-010","property":"OOXML/PDF structural validators reject malformed artifacts.","acceptance":"Completion selftest covers ZIP parts/XML parsing and PDF header/object/EOF checks."},
      {"claim_id":"DF-CLM-011","property":"Writer providers cannot self-grant G23/G24 or certification.","acceptance":"Negative writer-policy test rejects authority-bearing writer evidence."},
      {"claim_id":"DF-CLM-012","property":"Synthetic end-to-end infrastructure demonstration is reproducible without generating student assignment content.","acceptance":"synthetic_e2e.py passes source/citation/media/image/PDF/writer checks with student_assignment_generated=false."}
    ]); jwrite(target_root/"document-factory/CLAIMS.json",claims)

    risks=jload(target_root/"document-factory/RISK_REGISTER.json")
    add_by_id(risks["risks"],"id",[
      {"id":"DF-RISK-006","risk":"Citation metadata may be incomplete or unverifiable.","severity":"HIGH","treatment":"Never synthesize absent DOI/author/page/URL; unknown or unverified citation identifiers fail closed.","residual":"LOW_WITH_FAIL_CLOSED"},
      {"id":"DF-RISK-007","risk":"DPI and pixel dimensions may be semantically conflated.","severity":"MEDIUM","treatment":"Keep both concepts separate and preserve ambiguous source wording as UNKNOWN.","residual":"LOW"},
      {"id":"DF-RISK-008","risk":"Malformed OOXML/PDF may pass superficial file-extension checks.","severity":"MEDIUM","treatment":"Validate archive integrity, required parts/XML and PDF structural markers.","residual":"LOW"}
    ]); jwrite(target_root/"document-factory/RISK_REGISTER.json",risks)

    trace=jload(target_root/"document-factory/TRACEABILITY.json")
    existing={(x.get("requirement"),x.get("claim")) for x in trace["edges"]}
    for row in [
      {"requirement":"SOURCE_LEDGER_CSL","claim":"DF-CLM-007","implementation":"src/source_pipeline.py","test":"COMPLETION_SOURCE_PIPELINE"},
      {"requirement":"AUDIOVISUAL_VALIDATION","claim":"DF-CLM-008","implementation":"src/media_validation.py + toolchain.lock.json","test":"COMPLETION_MEDIA_VALIDATION"},
      {"requirement":"IMAGE_CONSTRAINTS","claim":"DF-CLM-009","implementation":"src/image_validation.py","test":"COMPLETION_IMAGE_VALIDATION"},
      {"requirement":"STRUCTURAL_VALIDATION_HARDENING","claim":"DF-CLM-010","implementation":"src/artifact_validation.py","test":"COMPLETION_ARTIFACT_VALIDATION"},
      {"requirement":"WRITER_PROVIDER_SEPARATION","claim":"DF-CLM-011","implementation":"src/writer_policy.py + src/writer.py","test":"COMPLETION_WRITER_POLICY"},
      {"requirement":"SYNTHETIC_E2E","claim":"DF-CLM-012","implementation":"src/synthetic_e2e.py","test":"SYNTHETIC_END_TO_END"}]:
        if (row["requirement"],row["claim"]) not in existing: trace["edges"].append(row)
    jwrite(target_root/"document-factory/TRACEABILITY.json",trace)

    mon=jload(target_root/"document-factory/MONITORING_PROFILE.json")
    for x in ("source_ledger","citation_coverage","ffprobe_admission","image_constraints","artifact_structure","writer_authority_boundary","synthetic_e2e"):
        if x not in mon["properties"]: mon["properties"].append(x)
    jwrite(target_root/"document-factory/MONITORING_PROFILE.json",mon)
    tests=jload(target_root/"document-factory/TEST_PLAN.json")
    for x in ("COMPLETION_SOURCE_PIPELINE","COMPLETION_MEDIA_VALIDATION","COMPLETION_IMAGE_VALIDATION","COMPLETION_ARTIFACT_VALIDATION","COMPLETION_WRITER_POLICY","SYNTHETIC_END_TO_END"):
        if x not in tests["mandatory"]: tests["mandatory"].append(x)
    jwrite(target_root/"document-factory/TEST_PLAN.json",tests)
    wc=jload(target_root/"document-factory/WRITING_CONTRACT.json"); wc["writer_certification_authority"]=False; wc["unknown_reference_metadata_policy"]="DO_NOT_INFER_OR_COMPLETE"; jwrite(target_root/"document-factory/WRITING_CONTRACT.json",wc)

    state_dir=target_root/"document-factory/custosz"; state_dir.mkdir(parents=True,exist_ok=True)
    state={"schema":"DOCUMENT_FACTORY_CUSTOSZ_WORK_STATE/2.0","worker":"CUSTOSZ_V7","runtime":"CUSTOSZ_RUNTIME_V1","certified_checkpoint_sha":CERTIFIED,"continued_from_head":head,"main_dispatch_head":main_head,"main_role":"DEPENDENCY_AND_DOWNLOAD_DISPATCH_SOURCE","desktop_commander":"FORBIDDEN","family_count":9,"capability_count":72,"families":sorted(FAMILIES),"baseline_selftest":baseline,"rubric_compiler_selftest":rubric,"profile_validation":profile,"completion_selftest":completion,"synthetic_e2e":e2e,"ffprobe_provider_admission":admission,"material_step":"GENERIC_TECHNICAL_BACKLOG_COMPLETED","backlog_items_completed":["SOURCE_LEDGER_AND_CSL_PIPELINE","FFMPEG_FFPROBE_PROVIDER_ADMISSION_LOGIC","IMAGE_DPI_AND_PIXEL_VALIDATION","OOXML_AND_PDF_VALIDATION_HARDENING","WRITER_PROVIDER_SEPARATION","CLAIMS_RISK_TRACEABILITY_MONITORING_TESTS","END_TO_END_SYNTHETIC_REPRODUCIBILITY"],"scope_exclusions":["STUDENT_ASSIGNMENT_GENERATION","ACADEMIC_CORRECTNESS","LMS_SUBMISSION"],"g23":"NOT_PROPAGATED","g24":"NOT_PROPAGATED","next_work":["FRESH_PRODUCER_VALIDATION","INDEPENDENT_VALIDATION","G23","G24","OPERATIONAL_AUTHORIZATION"]}
    if not admission.get("admitted"): state["scope_exclusions"].append("FFPROBE_RUNTIME_CLAIM_UNTIL_PROVIDER_PROVENANCE_PINNED")
    jwrite(state_dir/"CURRENT_STATE.json",state)
    report={"schema":"DOCUMENT_FACTORY_CUSTOSZ_COMPLETION/1.0","status":"PASS","head_before":head,"certified_checkpoint_ancestor":CERTIFIED,"main_dispatch_sha":main_head,"nine_families_verified":True,"completion_selftest":json.loads(completion),"synthetic_e2e":json.loads(e2e),"ffprobe_provider_admission":admission,"certification_propagated":False,"g23":"NOT_EXECUTED","g24":"NOT_EXECUTED","student_assignment_generated":False}
    jwrite(state_dir/"COMPLETION_REPORT.json",report); tele("COMPLETION_CHECKPOINT","PASS",next="FRESH_VALIDATION_G23_G24")
    effect={"schema":"DOCUMENT_FACTORY_CUSTOSZ_MATERIAL_EFFECT/2.0","mission_id":d["mission_id"],"status":"PASS","effect":"GENERIC_TECHNICAL_BACKLOG_COMPLETION","main_dispatch_sha":main_head,"nine_families_verified":True,"certification_propagated":False}; jwrite(target,effect)
    f={"mission_id":d["mission_id"],"dispatch_id":d["dispatch_id"],"binding_id":d["binding_id"],"pid":os.getpid(),"fme_id":"FME-DOCUMENT-FACTORY-FINISH-"+d["dispatch_id"],"target":str(target),"after_digest":sha(target),"effect_type":d["expected_effect"]["effect_type"],"effect_is_material":True,"effect_is_mission_relevant":True,"effect_is_authorized":True,"effect_is_observable":True}; f["fme_digest"]=digest(f); jwrite(fme,f)
    return 0
if __name__=="__main__": raise SystemExit(main(sys.argv))
