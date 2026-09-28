#!/usr/bin/env python3
import copy, hashlib, importlib.util, json, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("route_mission", ROOT/"scripts/mission_mailbox/route_mission.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

registry=json.loads((ROOT/"mission-mailbox/runtime-adapters/registry.json").read_text(encoding="utf-8"))
adapter=registry["adapters"][0]
adapter_path=ROOT/adapter["path"]
assert hashlib.sha256(adapter_path.read_bytes()).hexdigest()==adapter["sha256"]

def native(source_sha, mission_class):
    return {
      "source":{"sha256":source_sha},
      "mission_payload":{
        "required_capabilities_explicit":[],
        "routing_hints":{"values":["CUSTOSZ_RUNTIME"]},
        "directives_observed":{"MISSION_CLASS":[{"line":1,"value":mission_class}]}
      }
    }

# A binding-providing adapter may be selected without a prebound executor,
# but only for its exact source, class and location.
old=native(adapter["source_sha256"],"FORENSIC_OPERATIONAL_SERVER_HARDENING")
m,r=mod.adapter_match(registry,old,ROOT,False,"GITHUB_HOSTED_ONLY")
assert len(m)==1 and not r, (m,r)
assert m[0]["provides_executor_binding"] is True

# Location mismatch must fail closed.
m,r=mod.adapter_match(registry,old,ROOT,False,"SELF_HOSTED_LUNA_AUX")
assert not m and any("EXECUTION_LOCATION_MISMATCH" in x["reasons"] for x in r), r

# New final mission must not inherit the old TEST_ONLY adapter.
final=native("8191840debd98f8775e530a37d3d23770f148693af64689f8e0d187be037cb21","FINAL_SERVER_READY_CLOSURE")
m,r=mod.adapter_match(registry,final,ROOT,False,"SELF_HOSTED_LUNA_AUX")
assert not m, m
flat={reason for item in r for reason in item["reasons"]}
assert "SOURCE_SHA256_MISMATCH" in flat
assert "MISSION_CLASS_MISMATCH" in flat
assert "EXECUTION_LOCATION_MISMATCH" in flat

# An adapter that cannot provide binding cannot run from an unbound state.
reg2=copy.deepcopy(registry)
reg2["adapters"][0]["provides_executor_binding"]=False
m,r=mod.adapter_match(reg2,old,ROOT,False,"GITHUB_HOSTED_ONLY")
assert not m and any("EXECUTOR_UNBOUND_AND_ADAPTER_CANNOT_BIND" in x["reasons"] for x in r), r

print("MAILBOX_ROUTER_POLICY_SELFTEST=PASS")
