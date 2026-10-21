from pathlib import Path
import sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from super1200_core.foundation import (
 EnvironmentManager,ModelStore,ServicePlatform,APIRuntimeRegistry,ServiceMaterializer,
 JobQueueInterface,LocalDurableQueue,BackpressureEngine,RemoteBridgeAppProtocol,
 SupplyChainAssurance,BugKnowledgeBase,RepositoryAcquisitionEngine,RepositoryExportEngine
)
e=EnvironmentManager(); e.record("python","isolated"); assert e.snapshot()["python"]=="isolated"
m=ModelStore(); m.put("m1",{"revision":"r1"}); assert m.get("m1")["revision"]=="r1"
s=ServicePlatform(); s.deploy("svc","1","main"); assert s.status("svc")=="READY"
a=APIRuntimeRegistry(); a.register("get","/health","health"); assert a.resolve("GET","/health")=="health"
mat=ServiceMaterializer().materialize({"name":"svc","version":"1","entrypoint":"main"}); assert mat["state"]=="MATERIALIZED"
q=JobQueueInterface(); q.submit("j1",{}); assert q.pop()[0]=="j1"
dq=LocalDurableQueue(); dq.submit("j2",{"x":1}); snap=dq.snapshot(); dq.pop(); dq.restore(snap); assert len(dq)==1
bp=BackpressureEngine(2); assert bp.admit(1) and not bp.admit(2)
env=RemoteBridgeAppProtocol.envelope("r1",{"x":1}); assert RemoteBridgeAppProtocol.validate(env)
assert SupplyChainAssurance().verify("abc","abc") and not SupplyChainAssurance().verify("abc","def")
kb=BugKnowledgeBase(); kb.record("b1","cause","fix"); assert kb.lookup("b1")["remediation"]=="fix"
assert RepositoryAcquisitionEngine().acquire("repo","rev")["state"]=="ACQUIRED"
assert RepositoryExportEngine().export("a","digest")["state"]=="EXPORTED"
print("D01_CONTINUATION_TESTS=PASS")
