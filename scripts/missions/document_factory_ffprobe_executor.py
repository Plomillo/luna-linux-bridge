#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,time
from pathlib import Path

def digest_obj(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(argv):
    if len(argv)!=9: raise SystemExit("EXPECTED_8_ARGUMENTS")
    dispatch,ack,fme,target,main_root,target_root,mailbox_root,outdir=map(Path,argv[1:9])
    d=json.loads(dispatch.read_text(encoding="utf-8"))
    outdir.mkdir(parents=True,exist_ok=True)
    accepted={
      "mission_id":d["mission_id"],"dispatch_id":d["dispatch_id"],"executor_id":d["executor_id"],
      "accepted":True,"pid":os.getpid(),"process_or_execution_token":"custosz-ffprobe-provider-admission-supervised"
    }
    accepted["ack_digest"]=digest_obj(accepted)
    ack.write_text(json.dumps(accepted,sort_keys=True)+"\n",encoding="utf-8")

    supervisor=main_root/"scripts/missions/document_factory_ffprobe_supervisor.py"
    materializer=main_root/"scripts/missions/document_factory_ffprobe_materializer.py"
    launcher_log=outdir/"SUPERVISOR_LAUNCH.log"
    with launcher_log.open("w",encoding="utf-8") as log:
        p=subprocess.Popen(
          [sys.executable,"-B","-I",str(supervisor),str(materializer),str(target_root),str(main_root),str(mailbox_root),str(outdir)],
          stdout=log,stderr=log,text=True,start_new_session=True
        )

    heartbeat=outdir/"SUPERVISOR_HEARTBEAT.json"
    deadline=time.monotonic()+8
    while time.monotonic()<deadline and not heartbeat.is_file():
        if p.poll() is not None:
            raise SystemExit("SUPERVISOR_EXITED_BEFORE_HEARTBEAT:"+str(p.returncode))
        time.sleep(0.2)
    if not heartbeat.is_file():
        raise SystemExit("SUPERVISOR_HEARTBEAT_NOT_OBSERVED")

    lease={
      "schema":"CUSTOSZ_FFPROBE_EXECUTION_BINDING/1.0",
      "status":"RUNNING",
      "mission_id":d["mission_id"],
      "dispatch_id":d["dispatch_id"],
      "binding_id":d["binding_id"],
      "executor_pid":os.getpid(),
      "supervisor_pid":p.pid,
      "heartbeat_path":str(heartbeat),
      "completion_path":str(outdir/"SUPERVISOR_COMPLETION.json"),
      "final_result_path":str(outdir/"RESULT.json"),
      "certification_authority":False,
      "final_material_pass":False
    }
    target.write_text(json.dumps(lease,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    effect={
      "mission_id":d["mission_id"],"dispatch_id":d["dispatch_id"],"binding_id":d["binding_id"],
      "pid":os.getpid(),"fme_id":"FME-FFPROBE-BINDING-"+d["dispatch_id"],"target":str(target),
      "after_digest":sha(target),"effect_type":d["expected_effect"]["effect_type"],
      "effect_is_material":True,"effect_is_mission_relevant":True,"effect_is_authorized":True,"effect_is_observable":True,
      "effect_scope":"EXECUTION_BINDING_ONLY_NOT_FINAL_PROVIDER_ADMISSION",
      "supervisor_pid":p.pid,
      "heartbeat_path":str(heartbeat),
      "final_material_pass":False
    }
    effect["fme_digest"]=digest_obj(effect)
    fme.write_text(json.dumps(effect,sort_keys=True)+"\n",encoding="utf-8")

if __name__=="__main__":
    main(sys.argv)
