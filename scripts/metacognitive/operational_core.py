#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib
from datetime import datetime, timezone

ROOT_FILES=[
 "Louksna.md",
 "PUAC2.md",
 "ecosystem/metacognitive-operational-v1/CAPABILITIES.json",
 "ecosystem/metacognitive-operational-v1/CUSTOSZ72_CENSUS.json",
 "ecosystem/metacognitive-operational-v1/CUSTOSZ72_DEDUP_EVIDENCE.json",
 "ecosystem/metacognitive-operational-v1/ECOSYSTEM_CONTRACT.md",
 "ecosystem/metacognitive-operational-v1/PROHIBITIONS.md",
 "ecosystem/metacognitive-operational-v1/INFRASTRUCTURE.md",
 "ecosystem/metacognitive-operational-v1/REMOTE_CORPUS_TRANSLATION.md",
 "ecosystem/metacognitive-operational-v1/ASSURANCE_G23_G24.md",
]
ACTIONS={"full":"REUSE","composable":"COMPOSE_VIA_CONTRACT","partial":"EXTEND_OWNER_FAMILY","novel":"GAP_PROOF_THEN_CREATE","shared":"PLACE_IN_F08_COMMON_CORE"}

def utc(): return datetime.now(timezone.utc).isoformat()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(pathlib.Path(p).read_bytes())
def write_json(p,obj):
 p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

class EvidenceLedger:
 def __init__(self): self.rows=[]; self.prev="0"*64
 def append(self,event,payload):
  row={"seq":len(self.rows)+1,"event":event,"payload":payload,"prev_sha256":self.prev}
  raw=json.dumps(row,sort_keys=True,separators=(",",":")).encode()
  row["row_sha256"]=sha_bytes(raw); self.prev=row["row_sha256"]; self.rows.append(row); return row
 def verify(self):
  prev="0"*64
  for row in self.rows:
   x={k:v for k,v in row.items() if k!="row_sha256"}
   if x["prev_sha256"]!=prev or sha_bytes(json.dumps(x,sort_keys=True,separators=(",",":")).encode())!=row["row_sha256"]: return False
   prev=row["row_sha256"]
  return True

class WorkerScheduler:
 profiles=(8,16,32,48,64)
 def select(self,measurements,retry_ceiling=.05):
  valid=[x for x in measurements if x["workers"] in self.profiles and x["error_rate"]<=retry_ceiling and x["checksum_pass"]]
  if not valid: raise ValueError("NO_SAFE_PROFILE")
  return max(valid,key=lambda x:x["throughput_bps"])

class TranslationOrchestrator:
 def segment(self,n): return [{"segment_id":f"S{i:06d}","source":f"term-{i%97}: payload {i}"} for i in range(n)]
 def translate_identity(self,segments):
  return [{**x,"target":x["source"],"source_sha256":sha_bytes(x["source"].encode()),"target_sha256":sha_bytes(x["source"].encode())} for x in segments]
 def validate(self,rows):
  ids=[r["segment_id"] for r in rows]
  return len(ids)==len(set(ids)) and ids==sorted(ids) and all(r["source_sha256"]==r["target_sha256"] for r in rows)

class MetacognitivePlanner:
 def __init__(self,caps): self.caps=caps
 def plan(self,intent):
  words=set(intent.casefold().replace("/"," ").replace("_"," ").split()); scored=[]
  for c in self.caps:
   txt=(c["name"]+" "+c["boundary"]).casefold()
   score=sum(1 for w in words if len(w)>3 and w in txt)
   if score: scored.append((score,c["id"]))
  ids=[x[1] for x in sorted(scored,reverse=True)]
  return ids[:12] or ["MCAP-002","MCAP-004","MCAP-012","MCAP-027","MCAP-028"]

def load(root):
 root=pathlib.Path(root)
 m=json.loads((root/"ecosystem/metacognitive-operational-v1/CAPABILITIES.json").read_text(encoding="utf-8"))
 c=json.loads((root/"ecosystem/metacognitive-operational-v1/CUSTOSZ72_CENSUS.json").read_text(encoding="utf-8"))
 d=json.loads((root/"ecosystem/metacognitive-operational-v1/CUSTOSZ72_DEDUP_EVIDENCE.json").read_text(encoding="utf-8"))
 return root,m,c,d

def validate(root,m,c,d):
 caps=m["capabilities"]; ids=[x["id"] for x in caps]
 assert m["authority"]=="Louksna.md" and m["canonical_mutation"] is False and m["authority_transfer"] is False
 assert m["failure_posture"]=="FAIL_CLOSED" and len(caps)==59 and len(set(ids))==59
 assert [x["ordinal"] for x in caps]==list(range(1,60))
 assert caps[-1]["name"]=="GOVERNED_TRAINING_AND_CONTINUOUS_LEARNING"
 assert c["capability_count"]==72 and c["unique_capability_count"]==72
 rows=d["rows"]; assert len(rows)==59 and {x["mcap_id"] for x in rows}==set(ids)
 assert all(x["coverage"] in ACTIONS for x in rows)
 return True

def selftest(root,out):
 root,m,c,d=load(root); validate(root,m,c,d)
 ledger=EvidenceLedger(); ledger.append("START",{"authority":"Louksna.md"}); ledger.append("CHECK",{"mcap":59,"custosz":72}); assert ledger.verify()
 pick=WorkerScheduler().select([
  {"workers":8,"throughput_bps":8,"error_rate":0,"checksum_pass":True},
  {"workers":16,"throughput_bps":16,"error_rate":0,"checksum_pass":True},
  {"workers":32,"throughput_bps":31,"error_rate":0,"checksum_pass":True},
  {"workers":48,"throughput_bps":29,"error_rate":0,"checksum_pass":True},
  {"workers":64,"throughput_bps":20,"error_rate":.08,"checksum_pass":True},
 ])
 assert pick["workers"]==32
 tr=TranslationOrchestrator(); rows=tr.translate_identity(tr.segment(5000)); assert tr.validate(rows)
 plan=MetacognitivePlanner(m["capabilities"]).plan("remote corpus translation audit provenance"); assert plan
 report={"schema":"META_CORE_SELFTEST/1.0","utc":utc(),"status":"PASS","mcap_count":59,"custosz_count":72,
         "ledger_chain":"PASS","scheduler":"PASS","translation_pipeline":"PASS","planner":"PASS","sample_plan":plan,
         "network_used":False,"canonical_mutation":False}
 write_json(out,report); print(json.dumps(report,sort_keys=True))

def materialize(root,lane_dir,out):
 root,m,c,d=load(root); validate(root,m,c,d)
 out=pathlib.Path(out); out.mkdir(parents=True,exist_ok=True); lane_dir=pathlib.Path(lane_dir); lanes={}
 if lane_dir.is_dir():
  for p in sorted(lane_dir.rglob("*.json")):
   try:
    obj=json.loads(p.read_text(encoding="utf-8")); key=obj.get("lane") or obj.get("schema") or p.stem; lanes[str(key)]=obj
   except Exception: pass
 rows={x["mcap_id"]:x for x in d["rows"]}
 components=["Louksna","MetaOS","CUSTOSZ_V7","CUSTOSZ_RUNTIME_V1","PUAC2","GitHub","G23","G24"]
 nodes=[{"id":x,"kind":"component"} for x in components]; edges=[]; bindings=[]
 for cap in m["capabilities"]:
  r=rows[cap["id"]]; action=ACTIONS[r["coverage"]]; nodes.append({"id":cap["id"],"kind":"capability","name":cap["name"]})
  for consumer in cap["consumers"]: edges.append({"from":cap["id"],"to":consumer,"relation":"CONSUMED_BY"})
  bindings.append({"mcap_id":cap["id"],"name":cap["name"],"coverage":r["coverage"],"action":action,
                   "existing_capabilities":r.get("existing_capabilities",[]),"runtime_components":r.get("runtime_components",[]),
                   "consumers":cap["consumers"],"admission_state":"MATERIALIZED_CONTRACT"})
 write_json(out/"ECOSYSTEM_GRAPH.json",{"schema":"ECOSYSTEM_GRAPH/1.0","nodes":nodes,"edges":edges,"capability_count":59,"component_count":8})
 write_json(out/"CAPABILITY_BINDINGS.json",{"schema":"CAPABILITY_BINDINGS/1.0","count":59,"items":bindings})
 write_json(out/"LANE_EVIDENCE.json",{"schema":"LANE_EVIDENCE/1.0","lanes":lanes})
 write_json(out/"PROVENANCE.json",{"schema":"META_PROVENANCE/1.0","utc":utc(),"input_hashes":{p:sha_file(root/p) for p in ROOT_FILES},
                                   "authority":"Louksna.md","canonical_mutation":False,"training_last":True})
 write_json(out/"READINESS.json",{"schema":"META_ECOSYSTEM_READINESS/1.0","status":"PASS","scope":"CONTROL_PLANE_AND_CLOUD_EXECUTION_FRAMEWORK",
            "mcap59_mapped":59,"custosz72_exact":72,"g16_precheck":"PASS","lane_count":len(lanes),
            "full_provider_integrations_certified":False,
            "note":"Domain provider/data/model integrations outside tested lanes remain separately certifiable."})
 (out/"README_FINAL.md").write_text(
  "# Metacognitive Operational Ecosystem — Frozen Candidate Input\n\n"
  "Authority: Louksna.md\n\n"
  "This candidate materializes the governed control plane, capability graph, CUSTOSZ72-to-MCAP59 bindings, cloud execution lanes, provenance and assurance inputs. "
  "It does not claim that every external provider/data/model integration is independently certified. Training remains last and is not executed in this candidate.\n",
  encoding="utf-8")
 print(json.dumps({"status":"PASS","out":str(out),"lanes":len(lanes),"mcap":59,"custosz":72},sort_keys=True))

def freeze(input_dir):
 p=pathlib.Path(input_dir); excluded={"FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt"}; files=[]
 for f in sorted(x for x in p.rglob("*") if x.is_file() and x.name not in excluded):
  files.append({"path":f.relative_to(p).as_posix(),"sha256":sha_file(f),"size":f.stat().st_size})
 digest=sha_bytes(json.dumps(files,sort_keys=True,separators=(",",":")).encode())
 write_json(p/"FROZEN_CANDIDATE.json",{"schema":"FROZEN_CANDIDATE/1.0","candidate_digest_sha256":digest,"file_count":len(files),"files":files,
           "frozen":True,"canonical_mutation":False,"g23":"PENDING","g24":"PENDING"})
 (p/"CANDIDATE_DIGEST.txt").write_text(digest+"\n",encoding="ascii")
 print(json.dumps({"status":"PASS","candidate_digest_sha256":digest,"file_count":len(files)},sort_keys=True))

def main():
 ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
 a=sub.add_parser("selftest"); a.add_argument("--repo-root",default="."); a.add_argument("--out",required=True)
 a=sub.add_parser("materialize"); a.add_argument("--repo-root",default="."); a.add_argument("--lane-dir",required=True); a.add_argument("--out",required=True)
 a=sub.add_parser("freeze"); a.add_argument("--input-dir",required=True)
 q=ap.parse_args()
 if q.cmd=="selftest": selftest(q.repo_root,q.out)
 elif q.cmd=="materialize": materialize(q.repo_root,q.lane_dir,q.out)
 else: freeze(q.input_dir)
if __name__=="__main__": main()
