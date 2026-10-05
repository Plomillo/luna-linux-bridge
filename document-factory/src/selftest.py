#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,sys,tempfile,time,zipfile
SRC=pathlib.Path(__file__).resolve().parent
REPO=SRC.parents[1]
ROOT=SRC.parent
sys.path.insert(0,str(SRC))
from factory import validate_profile,body_word_count
from runtime import Heartbeat,append_audit,checkpoint,restore_checkpoint,run_stage,sha256_file,write_xlsx,verify_ooxml

def main():
    passed=[]
    profile=ROOT/"profiles"/"uniacc-neuroplasticidad-u2.json"
    data,failures=validate_profile(profile,REPO)
    assert not failures,failures
    assert abs(sum(float(x["points"]) for x in data["rubric"]["criteria"])-38.5)<1e-9
    assert len(data["rubric"]["criteria"])==10
    assert data["constraints"]["report_word_count"]=={"min":800,"max":1200,"exclude":["cover","bibliography"]}
    assert data["constraints"]["video"]["max_duration_seconds"]==300
    assert data["required_research"]["minimum_distinct_sources"]==3
    assert data["runtime_policy"]["heartbeat_interval_seconds"]==1
    assert data["unresolved_source_conflicts"][0]["state"]=="CONFLICT"
    assert data["unresolved_source_conflicts"][0]["resolution"]=="NOT_INFERRED"
    assert (REPO/data["raw_instruction_ref"]).is_file()
    passed.append("CURRENT_PROFILE_EXACT_CONTRACT")

    with tempfile.TemporaryDirectory() as td:
        t=pathlib.Path(td)/"bad-profile.json"
        bad=json.loads(json.dumps(data))
        bad["rubric"]["declared_total_points"]=38.4
        t.write_text(json.dumps(bad),encoding="utf-8")
        _,errors=validate_profile(t)
        assert any(x.startswith("RUBRIC_TOTAL_MISMATCH") for x in errors)
    passed.append("RUBRIC_ARITHMETIC_FAIL_CLOSED")

    with tempfile.TemporaryDirectory() as td:
        t=pathlib.Path(td)/"bad-heartbeat.json"
        bad=json.loads(json.dumps(data))
        bad["runtime_policy"]["heartbeat_interval_seconds"]=2
        t.write_text(json.dumps(bad),encoding="utf-8")
        _,errors=validate_profile(t)
        assert "HEARTBEAT_INTERVAL_NOT_ONE_SECOND" in errors
    passed.append("HEARTBEAT_POLICY_FAIL_CLOSED")

    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        (root/"source").mkdir(parents=True)
        (root/"source"/"report.md").write_text("<!-- BODY_START --> uno dos tres <!-- BODY_END -->",encoding="utf-8")
        assert body_word_count(root/"source"/"report.md")==3
        cp=checkpoint(root)
        assert cp["checkpoint_digest_sha256"]
        original_hash=sha256_file(root/"source"/"report.md")
        (root/"source"/"report.md").write_text("MUTATED",encoding="utf-8")
        proof=restore_checkpoint(root,cp["checkpoint_digest_sha256"])
        assert proof["status"]=="PASS"
        assert sha256_file(root/"source"/"report.md")==original_hash

        spec={"sheets":[{"name":"Audit","rows":[["id","status"],["T01","PASS"]]}]}
        write_xlsx(root/"a.xlsx",spec)
        assert verify_ooxml(root/"a.xlsx","xlsx")

        with Heartbeat(root,"SELFTEST",1):
            time.sleep(1.15)
        hb=json.loads((root/"runtime"/"heartbeat.json").read_text(encoding="utf-8"))
        assert hb["status"]=="STOPPED"

        h1=append_audit(root,{"event_type":"TEST","sequence":1})
        h2=append_audit(root,{"event_type":"TEST","sequence":2})
        rows=[json.loads(x) for x in (root/"evidence"/"audit.jsonl").read_text(encoding="utf-8").splitlines()]
        assert rows[-1]["previous_event_hash"]==h1
        assert rows[-1]["current_event_hash"]==h2
    passed.extend(["WORDCOUNT_BOUNDARY","CHECKPOINT","VERIFIED_ROLLBACK","XLSX_OOXML","ONE_SECOND_HEARTBEAT","AUDIT_HASH_CHAIN"])

    with tempfile.TemporaryDirectory() as td:
        bad=pathlib.Path(td)/"bad.docx"
        with zipfile.ZipFile(bad,"w") as z:
            z.writestr("[Content_Types].xml","x")
        try:
            verify_ooxml(bad,"docx")
            raise AssertionError("INVALID_OOXML_ACCEPTED")
        except ValueError:
            pass
    passed.append("INVALID_OOXML_REJECTED")

    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        try:
            run_stage(root,"TIMEOUT_NEGATIVE_TEST",[sys.executable,"-c","import time; time.sleep(2)"],1)
            raise AssertionError("TIMEOUT_NOT_ENFORCED")
        except RuntimeError as exc:
            assert str(exc)=="STAGE_TIMEOUT:TIMEOUT_NEGATIVE_TEST"
        state=json.loads((root/"runtime"/"hold.json").read_text(encoding="utf-8"))
        assert state["state"]=="HOLD"
        assert state["blind_retry"] is False
        assert state["resume_from"]=="LAST_VERIFIED_CHECKPOINT"
    passed.append("TIMEOUT_TO_HOLD_NO_BLIND_RETRY")

    recovery=json.loads((ROOT/"recovery.binding.json").read_text(encoding="utf-8"))
    assert recovery["duplicate_recovery_root"] is False
    assert recovery["reuse"]["contract"]=="recovery/RECOVERY_CONTRACT.json"
    passed.append("EXISTING_RECOVERY_ROOT_REUSED")

    result={"schema":"DOCUMENT_FACTORY_SELFTEST/1.0","status":"PASS","passed_count":len(passed),"tests":passed}
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
