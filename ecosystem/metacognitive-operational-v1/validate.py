#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
MANIFEST = ROOT / "CAPABILITIES.json"

def fail(code: str, detail: str) -> None:
    print(json.dumps({"status":"FAIL","code":code,"detail":detail}, ensure_ascii=False))
    raise SystemExit(2)

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args=ap.parse_args()
    data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    caps=data.get("capabilities",[])
    if data.get("authority")!="Louksna.md": fail("AUTHORITY","authority mismatch")
    if data.get("canonical_mutation") is not False: fail("CANONICAL_MUTATION","must be false")
    if data.get("authority_transfer") is not False: fail("AUTHORITY_TRANSFER","must be false")
    if data.get("failure_posture")!="FAIL_CLOSED": fail("FAILURE_POSTURE","must be FAIL_CLOSED")
    if len(caps)!=59 or data.get("capability_count")!=59: fail("COUNT",f"expected 59, got {len(caps)}")
    ords=[c["ordinal"] for c in caps]
    if ords!=list(range(1,60)): fail("ORDINALS","must be contiguous 1..59")
    names=[c["name"] for c in caps]
    if len(names)!=len(set(names)): fail("DUPLICATE_NAME","capability names must be unique")
    bounds=[c["boundary"] for c in caps]
    if len(bounds)!=len(set(bounds)): fail("DUPLICATE_BOUNDARY","functional boundaries must be unique")
    ids=[c["id"] for c in caps]
    if len(ids)!=len(set(ids)): fail("DUPLICATE_ID","IDs must be unique")
    if caps[-1]["name"]!="GOVERNED_TRAINING_AND_CONTINUOUS_LEARNING": fail("TRAINING_LAST","training must be ordinal 59")
    for c in caps:
        if c.get("creates_authority") is not False: fail("CAPABILITY_AUTHORITY",c["id"])
        if c.get("self_certifies") is not False: fail("SELF_CERTIFICATION",c["id"])
        consumers=c.get("consumers") or []
        if len(consumers)<2: fail("ORPHAN_CAPABILITY",c["id"])
        if not c.get("boundary"): fail("MISSING_BOUNDARY",c["id"])
        if c.get("duplicate_check")!="REQUIRED": fail("DUPLICATE_CHECK",c["id"])
    raw=MANIFEST.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    result={
      "status":"PASS",
      "scope":"STRUCTURAL_MANIFEST_VALIDATION_ONLY",
      "capability_count":len(caps),
      "manifest_sha256":sha,
      "canonical_mutation":False,
      "authority_transfer":False,
      "training_last":True,
      "custosz72_exact_diff":"OUT_OF_SCOPE_FOR_THIS_VALIDATOR",
      "g16_non_duplication":"OUT_OF_SCOPE_FOR_THIS_VALIDATOR",
      "g23":"OUT_OF_SCOPE_FOR_THIS_VALIDATOR",
      "g24":"OUT_OF_SCOPE_FOR_THIS_VALIDATOR",
      "certification_state_source":"BASE_CONTROLLED_INDEPENDENT_ASSURANCE_WORKFLOW_AND_PERSISTED_CERTIFICATION_RECORD"
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if args.out:
        out=pathlib.Path(args.out)
        out.mkdir(parents=True,exist_ok=True)
        (out/"VALIDATION.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/"README_VALIDATION.md").write_text(
            "# Metacognitive Ecosystem Validation\n\n"
            f"- Structural validation: **PASS**\n- Capability count: **{len(caps)}**\n"
            f"- Manifest SHA-256: `{sha}`\n"
            "- CUSTOSZ72 / G16: **OUT OF SCOPE FOR THIS STRUCTURAL VALIDATOR**\n"
            "- G23 / G24: **OUT OF SCOPE FOR THIS STRUCTURAL VALIDATOR**\n"
            "- Certification state source: **base-controlled independent assurance workflow + persisted certification record**\n"
            "\nThis structural PASS neither grants nor revokes certification.\n", encoding="utf-8")
if __name__=="__main__":
    main()
