import sys
from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parents[1]
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from super1200_core.foundation import (
    StateRegistry, CapabilityRegistry, DependencyManager, ArtifactStore,
    ServiceRegistry, HealthReadinessEngine, ResourceEnvelope,
    ObservabilityFabric, ProvenanceHistoryEngine, HoldReasonEngine,
    MetacognitiveStateEngine, DirectedGraph, ArchitecturalCostLedger,
    CostPredictionEngine,
)

s=StateRegistry(); s.set("x",1,source="test"); assert s.get("x")["value"]==1
c=CapabilityRegistry(); c.register(1,"STATE_REGISTRY",{})
try:
    c.register(1,"DUPLICATE",{})
    raise AssertionError("duplicate capability accepted")
except ValueError:
    pass
d=DependencyManager(); d.declare("c",["b"]); d.declare("b",["a"]); assert d.closure("c")==["a","b"]
d.declare("cycle",["cycle"])
try:
    d.closure("cycle")
    raise AssertionError("dependency cycle accepted")
except ValueError:
    pass
import tempfile
with tempfile.TemporaryDirectory() as td:
    a=ArtifactStore(td); h=a.put(b"abc"); assert a.get(h)==b"abc"
sr=ServiceRegistry(); sr.register("x","1","local","NONE"); assert sr.resolve("x")["version"]=="1"
assert HealthReadinessEngine.evaluate({"a":True})["ready"] is True
assert ResourceEnvelope(1,1,0,1).validate()
o=ObservabilityFabric(); o.emit("e1","TEST",{}); assert len(o.events)==1
try:
    o.emit("e1","DUP",{})
    raise AssertionError("duplicate event accepted")
except ValueError:
    pass
p=ProvenanceHistoryEngine(); p.record("o",["i"],"copy","h"); assert p.trace("o")["inputs"]==["i"]
h=HoldReasonEngine(); h.hold("x","R","C"); assert h.release("x",True)
m=MetacognitiveStateEngine(); assert m.compare("ACTIVE","DECLARED",None,None)["drift"] is True
g=DirectedGraph(); g.add("a","b"); g.add("b","c"); assert g.reachable("a")=={"b","c"}
l=ArchitecturalCostLedger(); l.record("x",1,2,3); assert l.totals()["bytes_written"]==3
assert CostPredictionEngine.predict([{"wall_s":2},{"wall_s":4}])["predicted_wall_s"]==3
print("D01_FOUNDATION_TESTS=PASS")
