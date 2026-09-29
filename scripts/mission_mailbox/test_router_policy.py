#!/usr/bin/env python3
import copy, hashlib, importlib.util, json, os, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("route_mission", ROOT/"scripts/mission_mailbox/route_mission.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

registry=json.loads((ROOT/"mission-mailbox/runtime-adapters/registry.json").read_text(encoding="utf-8"))
bindings=json.loads((ROOT/"mission-mailbox/source-class-bindings/registry.json").read_text(encoding="utf-8"))
by_id={a["adapter_id"]:a for a in registry["adapters"]}
old_adapter=by_id["SERVER_READY_CANDIDATE_V1"]
final_adapter=by_id["FINAL_SERVER_READY_CLOSURE_V1"]
meta_adapter=by_id["META_ECOSYSTEM_V1_ADMISSION"]

for adapter in (old_adapter, final_adapter, meta_adapter):
    path=ROOT/adapter["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==adapter["sha256"], adapter["adapter_id"]

def native(source_sha, mission_class=None):
    directives={}
    if mission_class is not None:
        directives["MISSION_CLASS"]=[{"line":1,"value":mission_class}]
    return {
      "source":{"sha256":source_sha},
      "mission_payload":{
        "required_capabilities_explicit":[],
        "routing_hints":{"values":["CUSTOSZ_RUNTIME"]},
        "directives_observed":directives
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

meta=native(meta_adapter["source_sha256"],None)
resolved=mod.resolve_mission_class(bindings,meta)
assert resolved["result"]=="PASS", resolved
assert resolved["mission_class"]=="METACOGNITIVE_ECOSYSTEM_V1", resolved
assert resolved["origin"]=="SOURCE_BOUND_REGISTRY", resolved
m,r=mod.adapter_match(
    registry,meta,ROOT,False,"SELF_HOSTED_LUNA_AUX",
    mission_class_override=resolved["mission_class"]
)
assert match_ids(m)=={"META_ECOSYSTEM_V1_ADMISSION"}, (m,r)

collision=native(meta_adapter["source_sha256"],"WRONG_CLASS")
resolved_collision=mod.resolve_mission_class(bindings,collision)
assert resolved_collision["result"]=="HOLD", resolved_collision
assert resolved_collision["root_blocker"]=="MISSION_CLASS_SOURCE_BINDING_COLLISION", resolved_collision

dupe=copy.deepcopy(bindings)
dupe["bindings"].append(copy.deepcopy(dupe["bindings"][0]))
resolved_dupe=mod.resolve_mission_class(dupe,meta)
assert resolved_dupe["result"]=="HOLD", resolved_dupe
assert resolved_dupe["root_blocker"]=="AMBIGUOUS_SOURCE_CLASS_BINDING", resolved_dupe

m,r=mod.adapter_match(
    registry,meta,ROOT,False,"GITHUB_HOSTED_ONLY",
    mission_class_override="METACOGNITIVE_ECOSYSTEM_V1"
)
assert "META_ECOSYSTEM_V1_ADMISSION" not in match_ids(m)
assert rejected(r,"META_ECOSYSTEM_V1_ADMISSION","EXECUTION_LOCATION_MISMATCH")

census=json.loads((ROOT/"ecosystem/metacognitive-operational-v1/CUSTOSZ72_CENSUS.json").read_text(encoding="utf-8"))
assert census["capability_count"]==72
assert census["unique_capability_count"]==72
assert census["pyz_sha256"]=="dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2"

# Workspace regression: a trusted workflow binding must not depend on a
# mounted Windows/PROYECTOS volume, and an invalid binding must fail closed.
old_override=os.environ.get("CUSTOSZ_WORKSPACE_OVERRIDE")
try:
    with tempfile.TemporaryDirectory(prefix="mailbox-workspace-selftest-") as td:
        os.environ["CUSTOSZ_WORKSPACE_OVERRIDE"]=td
        assert mod.find_workspace()==Path(td).resolve()
    os.environ["CUSTOSZ_WORKSPACE_OVERRIDE"]="/definitely/not/a/real/mailbox/workspace"
    try:
        mod.find_workspace()
    except RuntimeError as exc:
        assert str(exc).startswith("WORKSPACE_OVERRIDE_NOT_DIRECTORY:"), exc
    else:
        raise AssertionError("invalid workspace override did not fail closed")
finally:
    if old_override is None:
        os.environ.pop("CUSTOSZ_WORKSPACE_OVERRIDE",None)
    else:
        os.environ["CUSTOSZ_WORKSPACE_OVERRIDE"]=old_override

print("MAILBOX_ROUTER_POLICY_SELFTEST=PASS")
