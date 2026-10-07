#!/usr/bin/env python3
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
