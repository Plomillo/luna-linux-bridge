#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,sys,tempfile,time
SRC=pathlib.Path(__file__).resolve().parent
REPO=SRC.parents[1]
ROOT=SRC.parent
sys.path.insert(0,str(SRC))
from factory import validate_profile,body_word_count
from runtime import Heartbeat,append_audit,checkpoint,write_xlsx,verify_ooxml

def main():
    profile=ROOT/"profiles"/"uniacc-neuroplasticidad-u2.json"
    data,failures=validate_profile(profile,REPO)
    assert not failures,failures
    assert abs(sum(float(x["points"]) for x in data["rubric"]["criteria"])-38.5)<1e-9
    assert data["constraints"]["report_word_count"]=={"min":800,"max":1200,"exclude":["cover","bibliography"]}
    assert data["constraints"]["video"]["max_duration_seconds"]==300
    assert data["required_research"]["minimum_distinct_sources"]==3
    assert data["runtime_policy"]["heartbeat_interval_seconds"]==1
    assert data["unresolved_source_conflicts"][0]["state"]=="CONFLICT"
    assert data["unresolved_source_conflicts"][0]["resolution"]=="NOT_INFERRED"

    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        (root/"source").mkdir(parents=True)
        (root/"source"/"report.md").write_text(
            "<!-- BODY_START --> uno dos tres <!-- BODY_END -->",encoding="utf-8")
        assert body_word_count(root/"source"/"report.md")==3

        cp=checkpoint(root)
        assert cp["checkpoint_digest_sha256"]

        spec={"sheets":[{"name":"Audit","rows":[["id","status"],["T01","PASS"]]}]}
        write_xlsx(root/"a.xlsx",spec)
        assert verify_ooxml(root/"a.xlsx","xlsx")

        with Heartbeat(root,"SELFTEST",1):
            time.sleep(1.15)
        hb=json.loads((root/"runtime"/"heartbeat.json").read_text(encoding="utf-8"))
        assert hb["status"]=="STOPPED"

        h1=append_audit(root,{"event_type":"TEST","sequence":1})
        h2=append_audit(root,{"event_type":"TEST","sequence":2})
        lines=[json.loads(x) for x in (root/"evidence"/"audit.jsonl").read_text(encoding="utf-8").splitlines()]
        assert lines[-1]["previous_event_hash"]==h1
        assert lines[-1]["current_event_hash"]==h2

    print("DOCUMENT_FACTORY_SELFTEST=PASS")

if __name__=="__main__":
    main()
