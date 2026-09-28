#!/usr/bin/env python3
import copy, hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("route_mission", ROOT/"scripts/mission_mailbox/route_mission.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

registry=json.loads((ROOT/"mission-mailbox/runtime-adapters/registry.json").read_text(encoding="utf-8"))
by_id={a["adapter_id"]:a for a in registry["adapters"]}
old_adapter=by_id["SERVER_READY_CANDIDATE_V1"]
final_adapter=by_id["FINAL_SERVER_READY_CLOSURE_V1"]

for adapter in (old_adapter, final_adapter):
    path=ROOT/adapter["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==adapter["sha256"], adapter["adapter_id"]

def native(source_sha, mission_class):
    return {
      "source":{"sha256":source_sha},
      "mission_payload":{
        "required_capabilities_explicit":[],
        "routing_hints":{"values":["CUSTOSZ_RUNTIME"]},
        "directives_observed":{"MISSION_CLASS":[{"line":1,"value":mission_class}]}
      }
    }

def match_ids(matches):
    return {x["adapter_id"] for x in matches}

def rejected(rejections, adapter_id, reason):
    return any(x["adapter_id"]==adapter_id and reason in x["reasons"] for x in rejections)

old=native(old_adapter["source_sha256"],"FORENSIC_OPERATIONAL_SERVER_HARDENING")
m,r=mod.adapter_match(registry,old,ROOT,False,"GITHUB_HOSTED_ONLY")
assert match_ids(m)=={"SERVER_READY_CANDIDATE_V1"}, (m,r)
assert old_adapter["provides_executor_binding"] is True
assert rejected(r,"FINAL_SERVER_READY_CLOSURE_V1","SOURCE_SHA256_MISMATCH")

m,r=mod.adapter_match(registry,old,ROOT,False,"SELF_HOSTED_LUNA_AUX")
assert "SERVER_READY_CANDIDATE_V1" not in match_ids(m)
assert rejected(r,"SERVER_READY_CANDIDATE_V1","EXECUTION_LOCATION_MISMATCH")

final=native(final_adapter["source_sha256"],"FINAL_SERVER_READY_CLOSURE")
m,r=mod.adapter_match(registry,final,ROOT,False,"SELF_HOSTED_LUNA_AUX")
assert match_ids(m)=={"FINAL_SERVER_READY_CLOSURE_V1"}, (m,r)
assert rejected(r,"SERVER_READY_CANDIDATE_V1","SOURCE_SHA256_MISMATCH")
assert rejected(r,"SERVER_READY_CANDIDATE_V1","MISSION_CLASS_MISMATCH")
assert rejected(r,"SERVER_READY_CANDIDATE_V1","EXECUTION_LOCATION_MISMATCH")

reg2=copy.deepcopy(registry)
for a in reg2["adapters"]:
    if a["adapter_id"]=="FINAL_SERVER_READY_CLOSURE_V1":
        a["provides_executor_binding"]=False
m,r=mod.adapter_match(reg2,final,ROOT,False,"SELF_HOSTED_LUNA_AUX")
assert "FINAL_SERVER_READY_CLOSURE_V1" not in match_ids(m)
assert rejected(r,"FINAL_SERVER_READY_CLOSURE_V1","EXECUTOR_UNBOUND_AND_ADAPTER_CANNOT_BIND")

print("MAILBOX_ROUTER_POLICY_SELFTEST=PASS")
