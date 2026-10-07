from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, json, threading, time

class StateRegistry:
    def __init__(self): self._lock=threading.RLock(); self._state={}
    def set(self,key,value,*,source):
        if not source: raise ValueError("source required")
        with self._lock:
            self._state[key]={"value":value,"source":source,"observed_at":time.time()}
    def get(self,key): return self._state.get(key)
    def snapshot(self): return json.loads(json.dumps(self._state,sort_keys=True))

class CapabilityRegistry:
    def __init__(self): self._items={}
    def register(self,capability_id,name,contract):
        if capability_id in self._items: raise ValueError("duplicate capability")
        self._items[capability_id]={"id":capability_id,"name":name,"contract":contract}
    def get(self,capability_id): return self._items[capability_id]
    def ids(self): return sorted(self._items)

class DependencyManager:
    def __init__(self): self._deps={}
    def declare(self,node,deps): self._deps[node]=tuple(sorted(set(deps)))
    def closure(self,node):
        seen=set(); stack=[node]
        while stack:
            cur=stack.pop()
            for dep in self._deps.get(cur,()):
                if dep not in seen: seen.add(dep); stack.append(dep)
        if node in seen: raise ValueError("dependency cycle")
        return sorted(seen)

class ArtifactStore:
    def __init__(self,root):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
    def put(self,data:bytes):
        digest=hashlib.sha256(data).hexdigest(); p=self.root/digest
        if not p.exists(): p.write_bytes(data)
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest: raise IOError("CAS integrity")
        return digest
    def get(self,digest):
        data=(self.root/digest).read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest: raise IOError("CAS integrity")
        return data

class ServiceRegistry:
    def __init__(self): self._services={}
    def register(self,name,version,location,authority):
        self._services[name]={"version":version,"location":location,"authority":authority}
    def resolve(self,name): return self._services[name]

class HealthReadinessEngine:
    @staticmethod
    def evaluate(checks):
        checks=dict(checks)
        return {"ready":bool(checks) and all(checks.values()),"checks":checks}

@dataclass(frozen=True)
class ResourceEnvelope:
    cpu: float
    ram_bytes: int
    disk_bytes: int
    wallclock_seconds: int
    def validate(self):
        if self.cpu<=0 or self.ram_bytes<=0 or self.disk_bytes<0 or self.wallclock_seconds<=0:
            raise ValueError("invalid resource envelope")
        return True

class ObservabilityFabric:
    def __init__(self): self.events=[]
    def emit(self,event_id,kind,payload):
        if any(e["event_id"]==event_id for e in self.events): raise ValueError("duplicate event")
        self.events.append({"event_id":event_id,"kind":kind,"payload":payload})

class ProvenanceHistoryEngine:
    def __init__(self): self.nodes={}
    def record(self,obj_id,inputs,operation,output_hash):
        self.nodes[obj_id]={"inputs":list(inputs),"operation":operation,"output_hash":output_hash}
    def trace(self,obj_id): return self.nodes[obj_id]

class HoldReasonEngine:
    def __init__(self): self.holds={}
    def hold(self,key,reason,exit_condition):
        if not reason or not exit_condition: raise ValueError("typed reason and exit condition required")
        self.holds[key]={"reason":reason,"exit_condition":exit_condition}
    def release(self,key,condition_met):
        if not condition_met: return False
        self.holds.pop(key,None); return True

class MetacognitiveStateEngine:
    STATES=("DECLARED","EVIDENCED","VALIDATED","INDEPENDENTLY_VALIDATED","CERTIFIED","ACTIVE")
    def compare(self,pretended,observed,historical,certified):
        return {"pretended":pretended,"observed":observed,"historical":historical,"certified":certified,
                "drift":pretended!=observed or (certified is not None and observed!=certified)}

class DirectedGraph:
    def __init__(self): self.edges={}
    def add(self,a,b): self.edges.setdefault(a,set()).add(b)
    def reachable(self,start):
        seen=set(); stack=[start]
        while stack:
            cur=stack.pop()
            for nxt in self.edges.get(cur,set()):
                if nxt not in seen: seen.add(nxt); stack.append(nxt)
        return seen

class ArchitecturalCostLedger:
    def __init__(self): self.rows=[]
    def record(self,operation,cpu_s,wall_s,bytes_written):
        if min(cpu_s,wall_s,bytes_written)<0: raise ValueError("negative cost")
        self.rows.append({"operation":operation,"cpu_s":cpu_s,"wall_s":wall_s,"bytes_written":bytes_written})
    def totals(self):
        return {"cpu_s":sum(x["cpu_s"] for x in self.rows),
                "wall_s":sum(x["wall_s"] for x in self.rows),
                "bytes_written":sum(x["bytes_written"] for x in self.rows)}

class CostPredictionEngine:
    @staticmethod
    def predict(history):
        if not history: return {"predicted_wall_s":None,"confidence":"UNKNOWN"}
        vals=[float(x["wall_s"]) for x in history]
        return {"predicted_wall_s":sum(vals)/len(vals),"confidence":"EMPIRICAL"}
