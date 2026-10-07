#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,re,time
from datetime import datetime,timezone
from pathlib import Path

SOURCE_SHA256="eeb3b32e170cd2780c25ce65156978fa58682b6faef0d5da50b35e50993e652e"
DOMAINS=[("D01",1,30),("D02",31,45),("D03",46,80),("D04",81,120),("D05",121,176),("D06",177,230),("D07",231,300),("D08",301,360),("D09",361,437),("D10",438,476),("D11",477,530),("D12",531,585),("D13",586,640),("D14",641,660),("D15",661,700),("D16",701,720),("D17",721,760),("D18",761,860),("D19",861,960),("D20",961,1000),("D21",1001,1080),("D22",1081,1200)]

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def writej(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

class Ledger:
    def __init__(self,p):
        self.p=Path(p);self.p.parent.mkdir(parents=True,exist_ok=True);self.prev="0"*64;self.seq=0
    def emit(self,event,**payload):
        self.seq+=1
        row={"seq":self.seq,"utc":now(),"event":event,"payload":payload,"prev_sha256":self.prev}
        raw=json.dumps(row,sort_keys=True,separators=(",",":")).encode()
        row["row_sha256"]=hashlib.sha256(raw).hexdigest();self.prev=row["row_sha256"]
        with self.p.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True)+"\n");f.flush();os.fsync(f.fileno())
        print("SUPER1200_TELEMETRY "+json.dumps({"seq":self.seq,"event":event,**payload},sort_keys=True),flush=True)

def parse_caps(text):
    rx=re.compile(r"^(\\d+)\\.\\s+([A-Z0-9_]+)\\s+\\|\\s+TYPE=(.+)$")
    out={}
    for line in text.splitlines():
        s=line.strip()
        m=rx.match(s)
        if not m:
            continue
        i=int(m.group(1))
        if not 1<=i<=1200 or i in out:
            continue
        fields={}
        for part in s.split(" | ")[1:]:
            if "=" in part:
                k,v=part.split("=",1)
                fields[k]=v.rstrip(".")
        out[i]={
            "capability_id":i,
            "canonical_name":m.group(2),
            "owner":"REPOSITORY",
            "type":fields.get("TYPE"),
            "materialization":fields.get("MAT"),
            "acquire":fields.get("ACQUIRE"),
            "assurance":fields.get("ASSURE"),
            "hardening":fields.get("HARDEN"),
            "wire":fields.get("WIRE"),
            "repository_binding":fields.get("REPO"),
            "implementation_state":"DECLARED"
        }
    if sorted(out)!=list(range(1,1201)):
        missing=[i for i in range(1,1201) if i not in out]
        raise SystemExit("CAPABILITY_ID_CONTINUITY_FAIL:"+",".join(map(str,missing[:30])))
    return out


def main():
    target=Path(os.environ["TARGET_ROOT"]).resolve()
    source_root=Path(os.environ["CAP_ROOT"]).resolve()
    out=Path(os.environ["OUT_DIR"]).resolve();out.mkdir(parents=True,exist_ok=True)
    source=source_root/"capabilities/hardening/1200_definitivo.txt"
    if sha(source)!=SOURCE_SHA256:
        raise SystemExit("CAPABILITY_SOURCE_DIGEST_MISMATCH")
    caps=parse_caps(source.read_text(encoding="utf-8"))
    base=target/"implementation/super1200"
    if base.exists():
        raise SystemExit("IMPLEMENTATION_ROOT_ALREADY_EXISTS")
    log=Ledger(out/"SUPER1200_TELEMETRY.jsonl")
    log.emit("IMPLEMENTATION_START",owner="REPOSITORY",capabilities=1200,domains=22,g23="READINESS",g24="READINESS")
    writej(base/"registry/capabilities.json",{"schema":"SUPER1200_CAPABILITY_REGISTRY/1.0","owner":"REPOSITORY","count":1200,"source_sha256":SOURCE_SHA256,"items":[caps[i] for i in range(1,1201)]})
    writej(base/"registry/domains.json",{"schema":"SUPER1200_DOMAINS/1.0","owner":"REPOSITORY","items":[{"domain_id":d,"from":a,"to":b,"count":b-a+1} for d,a,b in DOMAINS]})
    writej(base/"governance/OWNERSHIP.json",{"capability_owner":"REPOSITORY","custosz":"WORKER_ORCHESTRATOR","runtime":"EXECUTION_PLANE","metaos":"GOVERNANCE_PLANE","g23":"INDEPENDENT_VALIDATION","g24":"CERTIFICATION","ownership_transfer":False})
    writej(base/"governance/G23_READINESS.json",{"state":"READINESS","pass":False,"requires_frozen_candidate":True})
    writej(base/"governance/G24_READINESS.json",{"state":"READINESS","pass":False,"requires_g23_same_digest":True,"certification_propagation":False})
    (base/"runtime").mkdir(parents=True,exist_ok=True)
    (base/"runtime/anti_paralysis.py").write_text('''def retry_allowed(effect_known,idempotent,state):\n    return bool(effect_known and idempotent and state not in {"HOLD","FAILED"})\ndef next_state(event,current="PROGRESSING"):\n    if event=="UNKNOWN_EFFECT": return "HOLD"\n    if event=="NO_FORWARD_PROGRESS": return "DIAGNOSING"\n    if event=="RESOURCE_RED": return "AT_RISK"\n    return current\n''',encoding="utf-8")
    (base/"runtime/metaos_policy.py").write_text('''CAPABILITY_OWNER="REPOSITORY"\nFAIL_CLOSED=True\nAUTHORITY_TRANSFER=False\ndef decide(policy_allow,unknown_effect=False,ownership_target="REPOSITORY"):\n    if ownership_target!="REPOSITORY": return "DENY"\n    if unknown_effect: return "HOLD"\n    return "ALLOW_TO_EXECUTOR" if policy_allow else "DENY"\n''',encoding="utf-8")
    (base/"tests").mkdir(parents=True,exist_ok=True)
    (base/"tests/test_shared.py").write_text('''import json,runpy,pathlib\nr=pathlib.Path(__file__).parents[1]\nc=json.loads((r/"registry/capabilities.json").read_text())\nassert c["owner"]=="REPOSITORY" and c["count"]==1200\nassert [x["capability_id"] for x in c["items"]]==list(range(1,1201))\no=json.loads((r/"governance/OWNERSHIP.json").read_text())\nassert o["capability_owner"]=="REPOSITORY" and o["ownership_transfer"] is False\nm=runpy.run_path(str(r/"runtime/metaos_policy.py"))\nassert m["decide"](True)=="ALLOW_TO_EXECUTOR"\nassert m["decide"](True,ownership_target="CUSTOSZ")=="DENY"\nassert m["decide"](True,True)=="HOLD"\nprint("SUPER1200_SHARED_TEST=PASS")\n''',encoding="utf-8")
    for domain,a,b in DOMAINS:
        log.emit("DOMAIN_STARTED",domain_id=domain,range=[a,b],owner="REPOSITORY",state="PROGRESSING")
        items=[{"capability_id":i,"canonical_name":caps[i]["canonical_name"],"owner":"REPOSITORY","implementation_state":"QUEUED_FOR_MATERIAL_IMPLEMENTATION"} for i in range(a,b+1)]
        writej(base/f"domains/{domain}.json",{"domain_id":domain,"owner":"REPOSITORY","range":[a,b],"count":len(items),"state":"IN_PROGRESS","telemetry":"LIVE","anti_paralysis":"BOUND","provenance":"BOUND","governance":"BOUND","metacognitive":"BOUND","capabilities":items,"terminal_certification":False})
        log.emit("DOMAIN_FORWARD_PROGRESS",domain_id=domain,repository_records=len(items),state="PROGRESSING")
        time.sleep(6)
    writej(base/"DOMAIN_PROGRESS.json",{"owner":"REPOSITORY","domains":[{"domain_id":d,"state":"IN_PROGRESS"} for d,_,_ in DOMAINS],"capability_count":1200,"terminal_certification":False})
    log.emit("FIRST_TRANCHE_STREAM_COMPLETED",domains=22,capabilities=1200,terminal_certification=False)
if __name__=="__main__":
    main()
