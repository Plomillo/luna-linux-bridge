#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys
from pathlib import Path

def digest_obj(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(argv):
    if len(argv)!=9: raise SystemExit("EXPECTED_8_ARGUMENTS")
    dispatch,ack,fme,target,main_root,target_root,mailbox_root,outdir=map(Path,argv[1:9])
    d=json.loads(dispatch.read_text(encoding="utf-8"))
    accepted={
      "mission_id":d["mission_id"],"dispatch_id":d["dispatch_id"],"executor_id":d["executor_id"],
      "accepted":True,"pid":os.getpid(),"process_or_execution_token":"custosz-ffprobe-provider-admission"
    }
    accepted["ack_digest"]=digest_obj(accepted)
    ack.write_text(json.dumps(accepted,sort_keys=True)+"\n",encoding="utf-8")
    materializer=main_root/"scripts/missions/document_factory_ffprobe_materializer.py"
    cmd=[sys.executable,"-B","-I",str(materializer),str(target_root),str(main_root),str(mailbox_root),str(outdir)]
    p=subprocess.run(cmd,text=True,stdout=None,stderr=None,timeout=2100)
    if p.returncode: raise SystemExit("FFPROBE_MATERIALIZER_FAILED:"+str(p.returncode))
    result=outdir/"RESULT.json"
    if not result.is_file(): raise SystemExit("FFPROBE_RESULT_MISSING")
    obj=json.loads(result.read_text(encoding="utf-8"))
    if obj.get("status")!="PASS": raise SystemExit("FFPROBE_RESULT_NOT_PASS")
    target.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    effect={
      "mission_id":d["mission_id"],"dispatch_id":d["dispatch_id"],"binding_id":d["binding_id"],
      "pid":os.getpid(),"fme_id":"FME-FFPROBE-"+d["dispatch_id"],"target":str(target),
      "after_digest":sha(target),"effect_type":d["expected_effect"]["effect_type"],
      "effect_is_material":True,"effect_is_mission_relevant":True,"effect_is_authorized":True,"effect_is_observable":True
    }
    effect["fme_digest"]=digest_obj(effect)
    fme.write_text(json.dumps(effect,sort_keys=True)+"\n",encoding="utf-8")
if __name__=="__main__": main(sys.argv)
