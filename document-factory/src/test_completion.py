#!/usr/bin/env python3
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
