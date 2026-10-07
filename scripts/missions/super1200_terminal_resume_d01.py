#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_HEAD="4e957f2d4a388a87f8dca17053e5f2ec8693c5a2"
RESUME_RUN=37652954550
FOUNDATION_IDS={1,2,3,5,10,11,15,18,19,21,22,23,24,25,26,27,28}
FOUNDATION_NAMES={
  1:"STATE_REGISTRY",2:"CAPABILITY_REGISTRY",3:"DEPENDENCY_MANAGER",5:"ARTIFACT_STORE",
  10:"SERVICE_REGISTRY",11:"HEALTH_READINESS_ENGINE",15:"RESOURCE_ENVELOPE_ENGINE",
  18:"OBSERVABILITY_FABRIC",19:"PROVENANCE_HISTORY_ENGINE",21:"HOLD_REASON_ENGINE",
  22:"METACOGNITIVE_STATE_ENGINE",23:"KNOWLEDGE_GRAPH",24:"DEPENDENCY_GRAPH",
  25:"CAPABILITY_GRAPH",26:"CERTIFICATION_GRAPH",27:"ARCHITECTURAL_COST_LEDGER",
  28:"COST_PREDICTION_ENGINE"
}
FOUNDATION_CODE="from __future__ import annotations\nfrom dataclasses import dataclass\nfrom pathlib import Path\nimport hashlib, json, threading, time\n\nclass StateRegistry:\n    def __init__(self): self._lock=threading.RLock(); self._state={}\n    def set(self,key,value,*,source):\n        if not source: raise ValueError(\"source required\")\n        with self._lock:\n            self._state[key]={\"value\":value,\"source\":source,\"observed_at\":time.time()}\n    def get(self,key): return self._state.get(key)\n    def snapshot(self): return json.loads(json.dumps(self._state,sort_keys=True))\n\nclass CapabilityRegistry:\n    def __init__(self): self._items={}\n    def register(self,capability_id,name,contract):\n        if capability_id in self._items: raise ValueError(\"duplicate capability\")\n        self._items[capability_id]={\"id\":capability_id,\"name\":name,\"contract\":contract}\n    def get(self,capability_id): return self._items[capability_id]\n    def ids(self): return sorted(self._items)\n\nclass DependencyManager:\n    def __init__(self): self._deps={}\n    def declare(self,node,deps): self._deps[node]=tuple(sorted(set(deps)))\n    def closure(self,node):\n        seen=set(); stack=[node]\n        while stack:\n            cur=stack.pop()\n            for dep in self._deps.get(cur,()):\n                if dep not in seen: seen.add(dep); stack.append(dep)\n        if node in seen: raise ValueError(\"dependency cycle\")\n        return sorted(seen)\n\nclass ArtifactStore:\n    def __init__(self,root):\n        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)\n    def put(self,data:bytes):\n        digest=hashlib.sha256(data).hexdigest(); p=self.root/digest\n        if not p.exists(): p.write_bytes(data)\n        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest: raise IOError(\"CAS integrity\")\n        return digest\n    def get(self,digest):\n        data=(self.root/digest).read_bytes()\n        if hashlib.sha256(data).hexdigest()!=digest: raise IOError(\"CAS integrity\")\n        return data\n\nclass ServiceRegistry:\n    def __init__(self): self._services={}\n    def register(self,name,version,location,authority):\n        self._services[name]={\"version\":version,\"location\":location,\"authority\":authority}\n    def resolve(self,name): return self._services[name]\n\nclass HealthReadinessEngine:\n    @staticmethod\n    def evaluate(checks):\n        checks=dict(checks)\n        return {\"ready\":bool(checks) and all(checks.values()),\"checks\":checks}\n\n@dataclass(frozen=True)\nclass ResourceEnvelope:\n    cpu: float\n    ram_bytes: int\n    disk_bytes: int\n    wallclock_seconds: int\n    def validate(self):\n        if self.cpu<=0 or self.ram_bytes<=0 or self.disk_bytes<0 or self.wallclock_seconds<=0:\n            raise ValueError(\"invalid resource envelope\")\n        return True\n\nclass ObservabilityFabric:\n    def __init__(self): self.events=[]\n    def emit(self,event_id,kind,payload):\n        if any(e[\"event_id\"]==event_id for e in self.events): raise ValueError(\"duplicate event\")\n        self.events.append({\"event_id\":event_id,\"kind\":kind,\"payload\":payload})\n\nclass ProvenanceHistoryEngine:\n    def __init__(self): self.nodes={}\n    def record(self,obj_id,inputs,operation,output_hash):\n        self.nodes[obj_id]={\"inputs\":list(inputs),\"operation\":operation,\"output_hash\":output_hash}\n    def trace(self,obj_id): return self.nodes[obj_id]\n\nclass HoldReasonEngine:\n    def __init__(self): self.holds={}\n    def hold(self,key,reason,exit_condition):\n        if not reason or not exit_condition: raise ValueError(\"typed reason and exit condition required\")\n        self.holds[key]={\"reason\":reason,\"exit_condition\":exit_condition}\n    def release(self,key,condition_met):\n        if not condition_met: return False\n        self.holds.pop(key,None); return True\n\nclass MetacognitiveStateEngine:\n    STATES=(\"DECLARED\",\"EVIDENCED\",\"VALIDATED\",\"INDEPENDENTLY_VALIDATED\",\"CERTIFIED\",\"ACTIVE\")\n    def compare(self,pretended,observed,historical,certified):\n        return {\"pretended\":pretended,\"observed\":observed,\"historical\":historical,\"certified\":certified,\n                \"drift\":pretended!=observed or (certified is not None and observed!=certified)}\n\nclass DirectedGraph:\n    def __init__(self): self.edges={}\n    def add(self,a,b): self.edges.setdefault(a,set()).add(b)\n    def reachable(self,start):\n        seen=set(); stack=[start]\n        while stack:\n            cur=stack.pop()\n            for nxt in self.edges.get(cur,set()):\n                if nxt not in seen: seen.add(nxt); stack.append(nxt)\n        return seen\n\nclass ArchitecturalCostLedger:\n    def __init__(self): self.rows=[]\n    def record(self,operation,cpu_s,wall_s,bytes_written):\n        if min(cpu_s,wall_s,bytes_written)<0: raise ValueError(\"negative cost\")\n        self.rows.append({\"operation\":operation,\"cpu_s\":cpu_s,\"wall_s\":wall_s,\"bytes_written\":bytes_written})\n    def totals(self):\n        return {\"cpu_s\":sum(x[\"cpu_s\"] for x in self.rows),\n                \"wall_s\":sum(x[\"wall_s\"] for x in self.rows),\n                \"bytes_written\":sum(x[\"bytes_written\"] for x in self.rows)}\n\nclass CostPredictionEngine:\n    @staticmethod\n    def predict(history):\n        if not history: return {\"predicted_wall_s\":None,\"confidence\":\"UNKNOWN\"}\n        vals=[float(x[\"wall_s\"]) for x in history]\n        return {\"predicted_wall_s\":sum(vals)/len(vals),\"confidence\":\"EMPIRICAL\"}\n"
TEST_CODE="import sys\nfrom pathlib import Path\n\nCORE_ROOT = Path(__file__).resolve().parents[1]\nif str(CORE_ROOT) not in sys.path:\n    sys.path.insert(0, str(CORE_ROOT))\n\nfrom super1200_core.foundation import (\n    StateRegistry, CapabilityRegistry, DependencyManager, ArtifactStore,\n    ServiceRegistry, HealthReadinessEngine, ResourceEnvelope,\n    ObservabilityFabric, ProvenanceHistoryEngine, HoldReasonEngine,\n    MetacognitiveStateEngine, DirectedGraph, ArchitecturalCostLedger,\n    CostPredictionEngine,\n)\n\ns=StateRegistry(); s.set(\"x\",1,source=\"test\"); assert s.get(\"x\")[\"value\"]==1\nc=CapabilityRegistry(); c.register(1,\"STATE_REGISTRY\",{})\ntry:\n    c.register(1,\"DUPLICATE\",{})\n    raise AssertionError(\"duplicate capability accepted\")\nexcept ValueError:\n    pass\nd=DependencyManager(); d.declare(\"c\",[\"b\"]); d.declare(\"b\",[\"a\"]); assert d.closure(\"c\")==[\"a\",\"b\"]\nd.declare(\"cycle\",[\"cycle\"])\ntry:\n    d.closure(\"cycle\")\n    raise AssertionError(\"dependency cycle accepted\")\nexcept ValueError:\n    pass\nimport tempfile\nwith tempfile.TemporaryDirectory() as td:\n    a=ArtifactStore(td); h=a.put(b\"abc\"); assert a.get(h)==b\"abc\"\nsr=ServiceRegistry(); sr.register(\"x\",\"1\",\"local\",\"NONE\"); assert sr.resolve(\"x\")[\"version\"]==\"1\"\nassert HealthReadinessEngine.evaluate({\"a\":True})[\"ready\"] is True\nassert ResourceEnvelope(1,1,0,1).validate()\no=ObservabilityFabric(); o.emit(\"e1\",\"TEST\",{}); assert len(o.events)==1\ntry:\n    o.emit(\"e1\",\"DUP\",{})\n    raise AssertionError(\"duplicate event accepted\")\nexcept ValueError:\n    pass\np=ProvenanceHistoryEngine(); p.record(\"o\",[\"i\"],\"copy\",\"h\"); assert p.trace(\"o\")[\"inputs\"]==[\"i\"]\nh=HoldReasonEngine(); h.hold(\"x\",\"R\",\"C\"); assert h.release(\"x\",True)\nm=MetacognitiveStateEngine(); assert m.compare(\"ACTIVE\",\"DECLARED\",None,None)[\"drift\"] is True\ng=DirectedGraph(); g.add(\"a\",\"b\"); g.add(\"b\",\"c\"); assert g.reachable(\"a\")=={\"b\",\"c\"}\nl=ArchitecturalCostLedger(); l.record(\"x\",1,2,3); assert l.totals()[\"bytes_written\"]==3\nassert CostPredictionEngine.predict([{\"wall_s\":2},{\"wall_s\":4}])[\"predicted_wall_s\"]==3\nprint(\"D01_FOUNDATION_TESTS=PASS\")\n"

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_text(p,s):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding="utf-8")
def writej(p,o):
    write_text(p,json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
def emit(event,**payload):
    print("SUPER1200_TELEMETRY "+json.dumps({"utc":utc(),"event":event,**payload},sort_keys=True),flush=True)
def run(cmd,env=None):
    return subprocess.run(cmd,text=True,capture_output=True,env=env,check=False)
def main():
    root=Path(os.environ["TARGET_ROOT"]).resolve()
    actual=run(["git","-C",str(root),"rev-parse","HEAD"])
    if actual.returncode or actual.stdout.strip()!=EXPECTED_HEAD:
        raise SystemExit(f"RESUME_HEAD_MISMATCH:{actual.stdout.strip()}")
    base=root/"implementation/super1200"
    regp=base/"registry/capabilities.json"
    d01p=base/"domains/D01.json"
    g23p=base/"governance/G23_READINESS.json"
    g24p=base/"governance/G24_READINESS.json"
    if not all(p.exists() for p in (regp,d01p,g23p,g24p)):
        raise SystemExit("RESUME_PRECONDITION_MISSING")
    reg=json.loads(regp.read_text(encoding="utf-8"))
    d01=json.loads(d01p.read_text(encoding="utf-8"))
    g23=json.loads(g23p.read_text(encoding="utf-8"))
    g24=json.loads(g24p.read_text(encoding="utf-8"))
    if reg.get("owner")!="REPOSITORY" or reg.get("count")!=1200:
        raise SystemExit("REGISTRY_IDENTITY_FAIL")
    if g23.get("pass") is not False or g24.get("pass") is not False:
        raise SystemExit("G23_G24_STATE_CHANGED_UNEXPECTEDLY")
    items={int(x["capability_id"]):x for x in reg["items"]}
    ditems={int(x["capability_id"]):x for x in d01["capabilities"]}
    if sorted(items)!=list(range(1,1201)) or sorted(ditems)!=list(range(1,31)):
        raise SystemExit("CAPABILITY_REGISTRY_CONTINUITY_FAIL")
    emit("D01_RESUME_PREFLIGHT",resume_run=RESUME_RUN,checkpoint_head=EXPECTED_HEAD,
         root_cause="PYTHONPATH_IGNORED_BY_ISOLATED_MODE",corrective_action="TEST_SELF_BOOTSTRAPS_CORE_ROOT",
         g23="BLOCKED_UNTIL_FUNCTIONAL_CLOSURE",g24="BLOCKED_UNTIL_G23_SAME_DIGEST",owner="REPOSITORY")
    core=root/"implementation/super1200/core"
    pkg=core/"super1200_core"
    tests=core/"tests"
    write_text(pkg/"__init__.py","from .foundation import *\n")
    write_text(pkg/"foundation.py",FOUNDATION_CODE)
    write_text(tests/"test_foundation.py",TEST_CODE)
    emit("D01_FOUNDATION_FILES_MATERIALIZED",capabilities=len(FOUNDATION_IDS),
         implementation_sha256=sha(pkg/"foundation.py"),test_sha256=sha(tests/"test_foundation.py"))
    result=run([sys.executable,"-B","-I",str(tests/"test_foundation.py")])
    if result.stdout: print(result.stdout,end="",flush=True)
    if result.stderr: print(result.stderr,end="",file=sys.stderr,flush=True)
    if result.returncode!=0:
        emit("D01_FOUNDATION_TESTS_FAILED",returncode=result.returncode,state="FAIL_CLOSED")
        raise SystemExit(result.returncode)
    for cid in FOUNDATION_IDS:
        name=FOUNDATION_NAMES[cid]
        item=items[cid]
        item["implementation_state"]="EVIDENCED"
        item["implementation_artifact"]="implementation/super1200/core/super1200_core/foundation.py"
        item["test_artifact"]="implementation/super1200/core/tests/test_foundation.py"
        ditem=ditems[cid]
        ditem["implementation_state"]="EVIDENCED"
        ditem["implementation_artifact"]="implementation/super1200/core/super1200_core/foundation.py"
        ditem["test_artifact"]="implementation/super1200/core/tests/test_foundation.py"
        if ditem.get("canonical_name")!=name:
            raise SystemExit(f"D01_CANONICAL_NAME_DRIFT:{cid}")
    reg["items"]=[items[i] for i in range(1,1201)]
    d01["capabilities"]=[ditems[i] for i in range(1,31)]
    d01["evidenced_capabilities"]=len(FOUNDATION_IDS)
    d01["pending_capabilities"]=30-len(FOUNDATION_IDS)
    d01["state"]="IN_PROGRESS"
    d01["terminal_certification"]=False
    writej(regp,reg); writej(d01p,d01)
    terminal=base/"terminal"
    writej(terminal/"D01_RESUME_37652954550.json",{
      "schema":"SUPER1200_D01_RESUME_EVIDENCE/1.0","mission_run":RESUME_RUN,
      "checkpoint_head":EXPECTED_HEAD,"owner":"REPOSITORY","domain_id":"D01",
      "evidenced_capabilities":sorted(FOUNDATION_IDS),"evidenced_count":len(FOUNDATION_IDS),
      "remaining_capabilities":1200-len(FOUNDATION_IDS),
      "root_cause":"PYTHONPATH_IGNORED_BY_ISOLATED_MODE",
      "corrective_action":"test_foundation.py inserts implementation/super1200/core into sys.path before package import",
      "test_command":[sys.executable,"-B","-I","implementation/super1200/core/tests/test_foundation.py"],
      "implementation_sha256":sha(pkg/"foundation.py"),"test_sha256":sha(tests/"test_foundation.py"),
      "g23":"BLOCKED_UNTIL_FUNCTIONAL_CLOSURE","g24":"BLOCKED_UNTIL_G23_SAME_DIGEST",
      "terminal_certification":False,"generated_utc":utc()
    })
    write_text(terminal/"D01_RESUME_TELEMETRY.jsonl","".join([
      json.dumps({"event":"D01_RESUME_PREFLIGHT","resume_run":RESUME_RUN,"checkpoint_head":EXPECTED_HEAD,"utc":utc()},sort_keys=True)+"\n",
      json.dumps({"event":"D01_MATERIAL_IMPLEMENTATION_PROGRESS","domain_id":"D01","evidenced":len(FOUNDATION_IDS),"remaining":1200-len(FOUNDATION_IDS),"utc":utc()},sort_keys=True)+"\n",
      json.dumps({"event":"D01_FOUNDATION_TESTS_PASS","tests":1,"utc":utc()},sort_keys=True)+"\n"
    ]))
    emit("D01_MATERIAL_IMPLEMENTATION_PROGRESS",domain_id="D01",evidenced=len(FOUNDATION_IDS),
         remaining=1200-len(FOUNDATION_IDS),g23="WAITING_FOR_FUNCTIONAL_CLOSURE",g24="WAITING_FOR_G23")
    emit("D01_FOUNDATION_TESTS_PASS",domain_id="D01",implementation_state="EVIDENCED")
if __name__=="__main__":
    main()
