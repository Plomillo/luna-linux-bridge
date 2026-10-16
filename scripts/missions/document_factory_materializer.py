#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys
from pathlib import Path

CHECKPOINT="067e1be0b13d9400c2c78d6174138c10ce980dd7"
FAMILIES={
 "F01_IO_KNOWLEDGE","F02_EXECUTION_RESOURCES","F03_SECURITY_TRUST",
 "F04_INTELLIGENCE_SYNTHESIS","F05_ASSURANCE_EPISTEMIC",
 "F06_CONTINUITY_INTEROP","F07_MEMORY_DOCUMENTATION",
 "F08_FORMAL_CORE","F09_CAPABILITY_GAPS_EVOLUTION"
}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def digest_obj(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def run(cmd,cwd=None,timeout=120):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError("COMMAND_FAIL:"+repr(cmd)+"\n"+p.stdout[-2500:]+"\n"+p.stderr[-2500:])
    return p.stdout.strip()

def compiler_source():
    return '''#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,pathlib

def compile_rubric(profile):
    rubric=profile.get("rubric") or {}
    criteria=rubric.get("criteria") or []
    obligations=[]
    total=0.0
    for row in criteria:
        cid=str(row.get("id","")).strip()
        if not cid:
            raise ValueError("RUBRIC_CRITERION_ID_MISSING")
        points=float(row.get("points",0))
        total+=points
        validation=str(row.get("validation","UNKNOWN"))
        obligations.append({
          "criterion_id":cid,
          "points":points,
          "requirement_text":row.get("text"),
          "validation_class":validation,
          "automated_assist":("AUTOMATED" in validation),
          "independent_or_human_required":("G23" in validation or "HUMAN" in validation),
          "claim_status":"UNKNOWN",
          "evidence_ref":None
        })
    declared=float(rubric.get("declared_total_points",-1))
    if abs(total-declared)>1e-9:
        raise ValueError(f"RUBRIC_TOTAL_MISMATCH:{total}!={declared}")
    return {
      "schema":"DOCUMENT_FACTORY_RUBRIC_OBLIGATIONS/1.0",
      "profile_id":profile.get("profile_id"),
      "profile_version":profile.get("profile_version"),
      "declared_total_points":declared,
      "criterion_count":len(obligations),
      "obligations":obligations,
      "certification_authority":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("profile")
    ap.add_argument("--out")
    args=ap.parse_args()
    profile=json.loads(pathlib.Path(args.profile).read_text(encoding="utf-8"))
    result=compile_rubric(profile)
    text=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\\n"
    if args.out:
        pathlib.Path(args.out).write_text(text,encoding="utf-8")
    else:
        print(text,end="")

if __name__=="__main__":
    main()
'''

def test_source():
    return '''#!/usr/bin/env python3
import json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from rubric_compiler import compile_rubric
p=json.loads((ROOT/"profiles/uniacc-neuroplasticidad-u2.json").read_text(encoding="utf-8"))
r=compile_rubric(p)
assert r["criterion_count"]==10
assert abs(r["declared_total_points"]-38.5)<1e-9
assert any(x["independent_or_human_required"] for x in r["obligations"])
assert all(x["claim_status"]=="UNKNOWN" for x in r["obligations"])
assert r["certification_authority"] is False
print("RUBRIC_COMPILER_SELFTEST=PASS")
'''

def main(argv):
    if len(argv)!=9:
        raise SystemExit("EXPECTED_8_ARGUMENTS")
    dispatch,ack,fme,target,mission_root,target_root,main_root,census_path=map(Path,argv[1:9])
    d=json.loads(dispatch.read_text(encoding="utf-8"))
    census=json.loads(census_path.read_text(encoding="utf-8"))
    families={x.get("family") for x in census.get("capabilities",[]) if x.get("family")}
    if census.get("family_count")!=9 or census.get("capability_count")!=72 or census.get("unique_capability_count")!=72 or not FAMILIES.issubset(families):
        raise SystemExit("CUSTOSZ_9_FAMILY_CENSUS_FAIL")
    head=run(["git","rev-parse","HEAD"],target_root)
    if head!=CHECKPOINT:
        raise SystemExit("CERTIFIED_CHECKPOINT_DRIFT:"+head)
    main_head=run(["git","rev-parse","HEAD"],main_root)

    accepted={"mission_id":d["mission_id"],"dispatch_id":d["dispatch_id"],"executor_id":d["executor_id"],"accepted":True,"pid":os.getpid(),"process_or_execution_token":"custosz-document-factory-runtime"}
    accepted["ack_digest"]=digest_obj(accepted)
    ack.write_text(json.dumps(accepted,sort_keys=True)+"\n",encoding="utf-8")

    before={}
    for rel in ("document-factory/src/factory.py","document-factory/src/runtime.py","document-factory/src/selftest.py","document-factory/AUTONOMOUS_CONTINUATION.md"):
        p=target_root/rel
        before[rel]=sha(p) if p.is_file() else None

    selftest=run([sys.executable,"-B","document-factory/src/selftest.py"],target_root)
    profiletest=run([sys.executable,"-B","document-factory/src/factory.py","validate-profile","document-factory/profiles/uniacc-neuroplasticidad-u2.json","--repo-root","."],target_root)

    src=target_root/"document-factory/src"
    src.mkdir(parents=True,exist_ok=True)
    (src/"rubric_compiler.py").write_text(compiler_source(),encoding="utf-8")
    (src/"test_rubric_compiler.py").write_text(test_source(),encoding="utf-8")
    rubrictest=run([sys.executable,"-B","document-factory/src/test_rubric_compiler.py"],target_root)

    state_dir=target_root/"document-factory/custosz"
    state_dir.mkdir(parents=True,exist_ok=True)
    state={
      "schema":"DOCUMENT_FACTORY_CUSTOSZ_WORK_STATE/1.0",
      "worker":"CUSTOSZ_V7",
      "runtime":"CUSTOSZ_RUNTIME_V1",
      "certified_checkpoint_sha":CHECKPOINT,
      "target_head_before":head,
      "main_dispatch_head":main_head,
      "main_role":"DEPENDENCY_AND_DOWNLOAD_DISPATCH_SOURCE",
      "desktop_commander":"FORBIDDEN",
      "family_count":9,
      "capability_count":72,
      "families":sorted(FAMILIES),
      "baseline_selftest":selftest,
      "profile_validation":profiletest,
      "material_step":"GENERIC_RUBRIC_COMPILER_IMPLEMENTED",
      "material_step_test":rubrictest,
      "before_hashes":before,
      "g23":"NOT_PROPAGATED",
      "g24":"NOT_PROPAGATED",
      "next_work":[
        "SOURCE_LEDGER_AND_CSL_PIPELINE",
        "FFMPEG_FFPROBE_PROVIDER_ADMISSION",
        "IMAGE_DPI_AND_PIXEL_VALIDATION",
        "OOXML_AND_PDF_VALIDATION_HARDENING",
        "END_TO_END_SYNTHETIC_REPRODUCIBILITY"
      ]
    }
    (state_dir/"CURRENT_STATE.json").write_text(json.dumps(state,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

    report={
      "schema":"DOCUMENT_FACTORY_CUSTOSZ_MATERIAL_EFFECT/1.0",
      "mission_id":d["mission_id"],
      "status":"PASS",
      "effect":"RUBRIC_COMPILER_PLUS_GOVERNED_STATE",
      "main_dispatch_sha":main_head,
      "nine_families_verified":True,
      "changed_files":[
        "document-factory/src/rubric_compiler.py",
        "document-factory/src/test_rubric_compiler.py",
        "document-factory/custosz/CURRENT_STATE.json"
      ],
      "certification_propagated":False
    }
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

    effect={"mission_id":d["mission_id"],"dispatch_id":d["dispatch_id"],"binding_id":d["binding_id"],"pid":os.getpid(),"fme_id":"FME-DOCUMENT-FACTORY-"+d["dispatch_id"],"target":str(target),"after_digest":sha(target),"effect_type":d["expected_effect"]["effect_type"],"effect_is_material":True,"effect_is_mission_relevant":True,"effect_is_authorized":True,"effect_is_observable":True}
    effect["fme_digest"]=digest_obj(effect)
    fme.write_text(json.dumps(effect,sort_keys=True)+"\n",encoding="utf-8")
    return 0

if __name__=="__main__":
    raise SystemExit(main(sys.argv))
