import json,runpy,pathlib
r=pathlib.Path(__file__).parents[1]
c=json.loads((r/"registry/capabilities.json").read_text())
assert c["owner"]=="REPOSITORY" and c["count"]==1200
assert [x["capability_id"] for x in c["items"]]==list(range(1,1201))
o=json.loads((r/"governance/OWNERSHIP.json").read_text())
assert o["capability_owner"]=="REPOSITORY" and o["ownership_transfer"] is False
m=runpy.run_path(str(r/"runtime/metaos_policy.py"))
assert m["decide"](True)=="ALLOW_TO_EXECUTOR"
assert m["decide"](True,ownership_target="CUSTOSZ")=="DENY"
assert m["decide"](True,True)=="HOLD"
print("SUPER1200_SHARED_TEST=PASS")
