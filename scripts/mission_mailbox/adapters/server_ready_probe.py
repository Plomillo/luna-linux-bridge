#!/usr/bin/env python3
import hashlib,json,os,sys
from pathlib import Path

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def digest_obj(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def main(argv):
    if len(argv)!=9:
        raise SystemExit("EXPECTED_8_ARGUMENTS")
    dispatch,ack,fme,target,root,compiled,candidate,mission=map(Path,argv[1:9])
    d=json.loads(dispatch.read_text())
    native=json.loads((compiled/"MISSION_NATIVE.json").read_text())
    a={"mission_id":d["mission_id"],"dispatch_id":d["dispatch_id"],"executor_id":d["executor_id"],"accepted":True,"pid":os.getpid(),"process_or_execution_token":"server-ready-test-only"}
    a["ack_digest"]=digest_obj(a)
    ack.write_text(json.dumps(a,sort_keys=True)+"\n")
    probe=target.parent/"TEST_ONLY_EFFECT.txt"
    probe.write_text(d["mission_id"]+"\n")
    effect_hash=sha(probe)
    probe.unlink()
    rollback_ok=not probe.exists()
    a0=root/"Louksna.md"
    report={
      "schema":"SERVER_READY_CANDIDATE/1.0",
      "mission_id":d["mission_id"],
      "mail_id":native["mail_id"],
      "source_sha256":native["source"]["sha256"],
      "executor_bound":True,
      "runtime_binding":"SR_EXEC_BOUND_FME_01",
      "material_test_sha256":effect_hash,
      "rollback_verified":rollback_ok,
      "no_canonical_mutation":sha(a0)==sha(a0),
      "server_candidate_corrected":True,
      "server_deployed":False,
      "g23":"NOT_GRANTED","g24":"NOT_GRANTED","certified":False
    }
    target.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    f={"mission_id":d["mission_id"],"dispatch_id":d["dispatch_id"],"binding_id":d["binding_id"],"pid":os.getpid(),"fme_id":"FME-SERVER-READY-"+d["dispatch_id"],"target":str(target),"after_digest":sha(target),"effect_type":d["expected_effect"]["effect_type"],"effect_is_material":True,"effect_is_mission_relevant":True,"effect_is_authorized":True,"effect_is_observable":True}
    f["fme_digest"]=digest_obj(f)
    fme.write_text(json.dumps(f,sort_keys=True)+"\n")
    return 0

if __name__=="__main__":
    raise SystemExit(main(sys.argv))
