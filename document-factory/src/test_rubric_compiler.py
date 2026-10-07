#!/usr/bin/env python3
import json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from rubric_compiler import compile_rubric
p=json.loads((ROOT/"profiles/uniacc-neuroplasticidad-u2.json").read_text(encoding="utf-8"))
r=compile_rubric(p)
assert r["criterion_count"]==10
assert abs(r["declared_total_points"]-38.5)<1e-9
assert any(x["independent_or_human_required"] for x in r["obligations"])
assert all(x["claim_status"]=="UNKNOWN" for x in r["obligations"])
assert r["certification_authority"] is False
print("RUBRIC_COMPILER_SELFTEST=PASS")
