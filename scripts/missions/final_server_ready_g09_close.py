#!/usr/bin/env python3
import argparse,hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path
MISSION_SHA="8191840debd98f8775e530a37d3d23770f148693af64689f8e0d187be037cb21"
REQUIRED_PRODUCER=["SERVER_READY_GATES.json","SERVICE_DEPLOYMENT_EVIDENCE.json","FAILURE_RECOVERY_EVIDENCE.json","RUNTIME_PROVENANCE.json","ROLLBACK_EVIDENCE.json","NON_REGRESSION_REPORT.json","RUN_MANIFEST.json","README_SERVER_READY_FINAL.md"]
def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def find(root,name):
 xs=list(Path(root).rglob(name))
 if len(xs)!=1: raise RuntimeError(f"{name}:EXPECTED_ONE_FOUND_{len(xs)}")
 return xs[0]
def dump(p,o):
 Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
def main():
 a=argparse.ArgumentParser();a.add_argument("--producer",required=True);a.add_argument("--postboot",required=True);a.add_argument("--g09",required=True);a.add_argument("--contract",required=True);a.add_argument("--out",required=True);q=a.parse_args()
 out=Path(q.out);evid=out/"evidence";evid.mkdir(parents=True,exist_ok=True)
 contract=json.loads(Path(q.contract).read_text())
 if contract["mission_sha256"]!=MISSION_SHA:raise SystemExit("CONTRACT_MISSION_IDENTITY_FAIL")
 copied={}
 for n in REQUIRED_PRODUCER:
  p=find(q.producer,n);dst=evid/n;shutil.copy2(p,dst);copied[n]=sha(dst)
 post=find(q.postboot,"BOOT_PERSISTENCE_EVIDENCE.json");shutil.copy2(post,evid/post.name);copied[post.name]=sha(evid/post.name)
 g09p=Path(q.g09).expanduser()
 if g09p.is_file():shutil.copy2(g09p,evid/"G09_FAILURE_RECOVERY_EVIDENCE.json")
 else:shutil.copy2(Path(q.contract).parent/"G09_FAILURE_RECOVERY_EVIDENCE.template.json",evid/"G09_FAILURE_RECOVERY_EVIDENCE.json")
 copied["G09_FAILURE_RECOVERY_EVIDENCE.json"]=sha(evid/"G09_FAILURE_RECOVERY_EVIDENCE.json")
 shutil.copy2(q.contract,evid/"SERVER_READY_TERMINAL_CHAIN_CONTRACT.json");copied["SERVER_READY_TERMINAL_CHAIN_CONTRACT.json"]=sha(evid/"SERVER_READY_TERMINAL_CHAIN_CONTRACT.json")
 base=json.loads((evid/"SERVER_READY_GATES.json").read_text());gates=dict(base["gates"])
 pb=json.loads((evid/"BOOT_PERSISTENCE_EVIDENCE.json").read_text());g09=json.loads((evid/"G09_FAILURE_RECOVERY_EVIDENCE.json").read_text())
 g08=pb.get("result")=="PASS"
 g09_pass=(g09.get("result")=="PASS" and g09.get("mission_sha256")==MISSION_SHA and g09.get("executor_kill_recovery") is True and g09.get("process_termination_recovery") is True and g09.get("runtime_failure_recovery") is True and g09.get("no_orphan_process") is True and g09.get("state_recovery") is True and g09.get("evidence_survives_restart") is True and g09.get("dependency_failure") in ("SAFE_RECOVERY","SAFE_HOLD") and g09.get("timeout") in ("SAFE_RECOVERY","SAFE_HOLD"))
 gates["GATE_08_SERVICE_PERSISTENCE"]="PASS" if g08 else "HOLD_BOOT_OBSERVATION_REQUIRED"
 gates["GATE_09_FAILURE_RECOVERY"]="PASS" if g09_pass else "HOLD_EXECUTOR_KILL_RECOVERY_REQUIRED"
 non_dynamic={k:v for k,v in gates.items() if k not in ("GATE_08_SERVICE_PERSISTENCE","GATE_09_FAILURE_RECOVERY")}
 static_pass=all(v=="PASS" for v in non_dynamic.values())
 all_pass=static_pass and g08 and g09_pass
 if not g08: current="G08";blocker=pb.get("root_blocker") or "BOOT_PERSISTENCE_NOT_PASS"
 elif not g09_pass: current="G09";blocker=g09.get("root_blocker") or "G09_RECOVERY_EVIDENCE_NOT_PASS"
 elif not static_pass: current="SERVER_READY_FREEZE";blocker=next(f"{k}={v}" for k,v in non_dynamic.items() if v!="PASS")
 else: current="G23";blocker=None
 terminal={"schema":"SERVER_READY_TERMINAL_GATES/1.0","utc":utc(),"mission_sha256":MISSION_SHA,"gates":gates,"server_ready":all_pass,"server_technical_ready":all_pass,"ready_for_g23":all_pass,"current_gate":current,"root_blocker":blocker,"global_mission_active":not all_pass}
 dump(out/"TERMINAL_GATES.json",terminal)
 state={"schema":"SERVER_READY_TERMINAL_CHAIN_STATE/1.0","utc":utc(),"G08":1 if g08 else 0,"G09":1 if g09_pass else 0,"G23":0,"G24":0,"CURRENT_GATE":current,"CHAIN_ACTIVE":1,"HOLD_IS_CHECKPOINT":1,"ROOT_BLOCKER":blocker,"NEXT_REQUIRED":"G23_INDEPENDENT_VALIDATION" if all_pass else current}
 dump(out/"CHAIN_STATE.json",state)
 events=[];parent="0"*64
 for name in sorted(copied):
  row={"utc":utc(),"event":"FROZEN_EVIDENCE","artifact":name,"sha256":copied[name],"parent_hash":parent}
  digest=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest();row["event_hash"]=digest;parent=digest;events.append(row)
 row={"utc":utc(),"event":"TERMINAL_GATE_EVALUATION","G08":state["G08"],"G09":state["G09"],"current_gate":current,"root_blocker":blocker,"parent_hash":parent}
 row["event_hash"]=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest();events.append(row);parent=row["event_hash"]
 (out/"EVIDENCE_CHAIN.jsonl").write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in events))
 manifest={"schema":"SERVER_READY_TERMINAL_BUNDLE_MANIFEST/1.0","utc":utc(),"mission_sha256":MISSION_SHA,"evidence_head":parent,"files":{p.name:sha(p) for p in sorted(evid.iterdir()) if p.is_file()}|{"TERMINAL_GATES.json":sha(out/"TERMINAL_GATES.json"),"CHAIN_STATE.json":sha(out/"CHAIN_STATE.json"),"EVIDENCE_CHAIN.jsonl":sha(out/"EVIDENCE_CHAIN.jsonl")}}
 dump(out/"FROZEN_BUNDLE_MANIFEST.json",manifest)
 print(json.dumps({"G08":state["G08"],"G09":state["G09"],"ready_for_g23":all_pass,"current_gate":current,"root_blocker":blocker},sort_keys=True))
 return 0
if __name__=="__main__":raise SystemExit(main())
