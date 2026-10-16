#!/usr/bin/env python3
import importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("route_mission", ROOT/"scripts/mission_mailbox/route_mission.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

policy=json.loads((ROOT/"mission-mailbox/config/mailbox-policy.json").read_text(encoding="utf-8"))
registry=json.loads((ROOT/policy["paths"]["adapter_registry"]).read_text(encoding="utf-8"))
bindings=json.loads((ROOT/policy["paths"]["source_class_bindings"]).read_text(encoding="utf-8"))
source_sha="1f8ba16e26789cc4ba3c9329357ac7c866af50177ccbf5915ca1dd5355c511d0"

def native(direct=None):
    directives={}
    if direct is not None:
        directives["MISSION_CLASS"]=[{"line":1,"value":direct}]
    return {
      "source":{"sha256":source_sha},
      "mission_payload":{
        "required_capabilities_explicit":[],
        "routing_hints":{"values":["CUSTOSZ_RUNTIME"]},
        "directives_observed":directives
      }
    }

n=native()
res=mod.resolve_mission_class(bindings,n)
assert res["result"]=="PASS",res
assert res["mission_class"]=="METACOGNITIVE_ECOSYSTEM_V1",res
assert res["origin"]=="SOURCE_BOUND_REGISTRY",res

collision=mod.resolve_mission_class(bindings,native("OTHER_CLASS"))
assert collision["result"]=="HOLD",collision
assert collision["root_blocker"]=="MISSION_CLASS_SOURCE_BINDING_COLLISION",collision

matches,rejected=mod.adapter_match(
    registry,n,ROOT,False,"SELF_HOSTED_LUNA_AUX",
    mission_class_override=res["mission_class"]
)
ids={x["adapter_id"] for x in matches}
assert ids=={"META_ECOSYSTEM_V1_ADMISSION"},(matches,rejected)

matches_wrong,rejected_wrong=mod.adapter_match(
    registry,n,ROOT,False,"GITHUB_HOSTED_ONLY",
    mission_class_override=res["mission_class"]
)
assert "META_ECOSYSTEM_V1_ADMISSION" not in {x["adapter_id"] for x in matches_wrong}
assert any(
    x["adapter_id"]=="META_ECOSYSTEM_V1_ADMISSION" and "EXECUTION_LOCATION_MISMATCH" in x["reasons"]
    for x in rejected_wrong
),rejected_wrong

census=ROOT/policy["paths"]["capability_census"]
inv=mod.capability_inventory({},census,"dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2")
assert inv["dedup_evidence_available"] is True,inv
assert len(inv["capabilities"])==72,inv
assert inv["source"]=="PINNED_CUSTOSZ72_CENSUS",inv

print(json.dumps({
  "status":"PASS",
  "source_bound_class":res["mission_class"],
  "selected_adapter":"META_ECOSYSTEM_V1_ADMISSION",
  "capability_census_count":len(inv["capabilities"]),
  "collision_test":"PASS",
  "wrong_location_test":"PASS"
},sort_keys=True))
