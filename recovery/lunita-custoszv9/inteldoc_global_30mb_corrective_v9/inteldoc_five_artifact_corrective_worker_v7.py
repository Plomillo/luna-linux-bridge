#!/usr/bin/env python3
"""CUSTOSZ V9 corrective worker V7: structural package candidate, no functional tests."""
from __future__ import annotations
import datetime as dt, hashlib, json, os, pathlib, shutil, subprocess, time

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
BASE=HOME/"PROYECTOS/1. PROYECTOS PRIORITARIOS"
OP=BASE/"5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
CONT=OP/"CUSTOSZ_CONTINUITY_V1"
LANE=CONT/"state/jobs/inteldoc_global_30mb_corrective_v9"
MISSION=LANE/"INTELDOC_GLOBAL_30MB_CORRECTIVE_MISSION.json"
ROOT=CONT/"state/jobs/inteldoc_global_30mb_corrective_worker_v9"
PREV=CONT/"state/jobs/inteldoc_global_30mb_corrective_worker_v8/candidate_staging_20261021T201814Z"
CAP=30_000_000
KNOWN_PYTHON_RUNTIME_BYTES=1_051_798_942

def utc():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def sha(p):
    h=hashlib.sha256()
    with pathlib.Path(p).open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""): h.update(b)
    return h.hexdigest()
def atomic(p,obj):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    tmp=p.with_name(p.name+".tmp")
    with tmp.open("x",encoding="utf-8") as f:
        json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
    os.chmod(tmp,0o600); os.replace(tmp,p)
def tree_inventory(p):
    items=[]
    for q in sorted(pathlib.Path(p).rglob("*")):
        if q.is_file():
            items.append({"path":str(q.relative_to(p)),"bytes":q.stat().st_size,"sha256":sha(q)})
    return {"path":str(p),"files":len(items),"bytes":sum(x["bytes"] for x in items),"entries":items}
def source_inventory(spec):
    root=pathlib.Path(spec["inventory"]["source_root"]); rows={}
    for item in spec["inventory"]["pinned_originals"]:
        p=root/item["path"]
        if not p.is_file(): raise RuntimeError("SOURCE_MISSING:"+item["id"])
        n=p.stat().st_size; h=sha(p)
        if n!=item["bytes"] or h!=item["sha256"]: raise RuntimeError("SOURCE_PIN_MISMATCH:"+item["id"])
        rows[item["id"]]={"path":str(p),"bytes":n,"sha256":h,"read_only":True}
    return rows
def find_host_tools():
    names=("ebook-convert","calibre","libreoffice","soffice","pdftotext","pdftoppm","tesseract","llama-cli","llama-mtmd-cli","llama-server","ollama")
    out=[]
    for name in names:
        path=shutil.which(name)
        rec={"name":name,"available":bool(path),"path":path}
        if path:
            try:
                q=pathlib.Path(path).resolve(); rec["resolved_path"]=str(q); rec["bytes"]=q.stat().st_size; rec["sha256"]=sha(q)
            except Exception as e: rec["inventory_error"]=type(e).__name__+":"+str(e)
        out.append(rec)
    return out
def main():
    started=time.monotonic()
    spec=json.loads(MISSION.read_text(encoding="utf-8"))
    inv=source_inventory(spec)
    originals=sum(x["bytes"] for x in inv.values())
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    stage=ROOT/("candidate_staging_"+stamp)
    if stage.exists(): raise RuntimeError("APPEND_ONLY_STAGE_COLLISION")
    stage.mkdir(parents=True,exist_ok=False,mode=0o700)
    cp=CONT/"state/checkpoints"/("INTELDOC_GLOBAL_30MB_V9_CANDIDATE_PRESTART_"+stamp)
    cp.mkdir(parents=True,exist_ok=False,mode=0o700)
    atomic(cp/"MANIFEST.json",{"schema":"INTELDOC_V9_PRESTART/1.0","timestamp_utc":utc(),
        "source_inventory":inv,"source_files_modified":False,"mission_sha256":sha(MISSION),
        "functional_tests":"NOT_RUN_BY_USER_INSTRUCTION","runtime_smoke":"NOT_RUN_BY_USER_INSTRUCTION"})
    prior_compact=PREV/"compact_combined_candidate/docling/compact_upstream_hf_candidate"
    prior_wheel=PREV/"direct_per_file_candidates/docling/docling_slim-2.124.0-pruned.whl"
    if not prior_compact.is_dir() or tree_inventory(prior_compact)["bytes"]!=20_871_887:
        raise RuntimeError("PINNED_COMPACT_MODEL_CANDIDATE_MISSING_OR_SIZE_MISMATCH")
    if not prior_wheel.is_file() or prior_wheel.stat().st_size!=775_392 or sha(prior_wheel)!="471a1bea5431ea264201d3781efe0b9d35b547357dfd0e483e4943f2127c974f":
        raise RuntimeError("PINNED_PRUNED_WHEEL_MISSING_OR_HASH_MISMATCH")
    pkg=stage/"compact_payload"; doc=pkg/"docling"; cal=pkg/"calibre"
    doc.mkdir(parents=True,exist_ok=False); cal.mkdir(parents=True,exist_ok=False)
    shutil.copytree(prior_compact,doc/"compact_upstream_hf_candidate",copy_function=shutil.copy2)
    shutil.copy2(prior_wheel,doc/"docling_slim-2.124.0-pruned.whl")
    # Calibre payload is not falsely represented as compressed: the original binary/source are replaced in this candidate
    # by explicit externalization records. This is a packaging experiment, not evidence of feature equivalence.
    calibre_bin=inv["CALIBRE_BINARY"]; calibre_src=inv["CALIBRE_SOURCE"]
    atomic(cal/"CALIBRE_BINARY_EXTERNALIZATION.json",{
        "schema":"INTELDOC_EXTERNALIZED_ARTIFACT/1.0","source_id":"CALIBRE_BINARY",
        "original_path":calibre_bin["path"],"original_bytes":calibre_bin["bytes"],"original_sha256":calibre_bin["sha256"],
        "bundled_binary":False,"host_calibre_detected":any(x["name"] in ("calibre","ebook-convert") and x["available"] for x in find_host_tools()),
        "equivalence":"NOT_ESTABLISHED","functional_tests":"NOT_RUN"})
    atomic(cal/"CALIBRE_SOURCE_PROVENANCE.json",{
        "schema":"INTELDOC_EXTERNALIZED_ARTIFACT/1.0","source_id":"CALIBRE_SOURCE",
        "original_path":calibre_src["path"],"original_bytes":calibre_src["bytes"],"original_sha256":calibre_src["sha256"],
        "bundled_source_archive":False,"role":"BUILD_PROVENANCE_ONLY_IN_THIS_EXPERIMENT",
        "equivalence":"NOT_ESTABLISHED","functional_tests":"NOT_RUN"})
    host_tools=find_host_tools()
    atomic(pkg/"HOST_TOOL_INVENTORY.json",{"schema":"INTELDOC_HOST_TOOL_INVENTORY/1.0",
        "collected_at_utc":utc(),"inventory_only_not_execution":True,"tools":host_tools})
    payload=tree_inventory(pkg)
    # The known Torch/Transformers runtime closure was measured in V8. It is still a required dependency for this
    # compact Hugging Face candidate; therefore payload-only PASS cannot be promoted to global-gross PASS.
    runtime_charge=KNOWN_PYTHON_RUNTIME_BYTES
    gross=payload["bytes"]+runtime_charge
    originals_after=source_inventory(spec)
    if originals_after!=inv: raise RuntimeError("ORIGINAL_SOURCE_MUTATION_DETECTED")
    result={
      "schema":"INTELDOC_GLOBAL_30MB_CORRECTIVE_V9_RESULT/1.0","mission_id":spec["mission_id"],
      "started_at_utc":utc(),"finished_at_utc":utc(),"elapsed_seconds":round(time.monotonic()-started,2),
      "status":"HOLD_OVER_GLOBAL_GROSS_CAP_OR_EXTERNALIZED_DEPENDENCIES",
      "phase":"STRUCTURAL_CANDIDATE_AND_RUNTIME_CLOSURE_GATE","hard_cap_bytes":CAP,
      "original_artifact_total_bytes":originals,"original_sources_modified":False,
      "candidate_payload":payload,
      "payload_gate":{"bytes":payload["bytes"],"hard_cap_bytes":CAP,"status":"PASS" if payload["bytes"]<=CAP else "HOLD_OVER_CAP","headroom_bytes":CAP-payload["bytes"]},
      "global_gross_gate":{"candidate_payload_bytes":payload["bytes"],"known_required_python_runtime_dependency_charge_bytes":runtime_charge,
          "minimum_gross_charged_bytes":gross,"additional_calibre_runtime_dependency_charge":"UNRESOLVED_HOST_CALIBRE_NOT_DETECTED",
          "hard_cap_bytes":CAP,"status":"PASS" if gross<=CAP else "HOLD_OVER_CAP","overage_bytes":max(0,gross-CAP),
          "global_target_met":gross<=CAP},
      "candidate_transform":{
        "CALIBRE_BINARY":"EXTERNALIZED_DESCRIPTOR_ONLY; original 192898432-byte archive not included in payload",
        "CALIBRE_SOURCE":"PROVENANCE_DESCRIPTOR_ONLY; original 48867616-byte source archive not included in payload",
        "DOCLING_WHEEL":"PINNED_REDUCED_WHEEL_REUSED",
        "DOCLING_GGUF_TEXT_AND_MMPROJ":"REPLACED_BY_SEPARATE_COMPACT_UPSTREAM_HF_CANDIDATE; equivalence not established"},
      "host_tools":host_tools,"functional_tests":"NOT_RUN_BY_USER_INSTRUCTION","runtime_smoke":"NOT_RUN_BY_USER_INSTRUCTION",
      "model_loading_or_generation":"NOT_RUN","quality_equivalence":"NOT_ESTABLISHED",
      "certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED",
      "prestart_checkpoint":str(cp),"original_hashes_after":originals_after,
      "next_required_strategy":"A native or otherwise dependency-light inference runtime is required before this payload can pass the strict global-gross 30000000-byte gate. Do not count externalized Calibre as resolved."
    }
    atomic(ROOT/"result.json",result)
    atomic(ROOT/"progress.json",{"schema":"INTELDOC_GLOBAL_30MB_CORRECTIVE_PROGRESS/2.0","updated_at_utc":utc(),
      "status":result["status"],"phase":result["phase"],"candidate_payload_bytes":payload["bytes"],
      "global_gross_minimum_bytes":gross,"hard_cap_bytes":CAP,"global_target_met":False,
      "functional_tests":"NOT_RUN_BY_USER_INSTRUCTION","result_path":str(ROOT/"result.json")})
    print(json.dumps({"status":result["status"],"candidate_payload_bytes":payload["bytes"],
      "payload_gate":result["payload_gate"],"global_gross_gate":result["global_gross_gate"],
      "result_path":str(ROOT/"result.json"),"functional_tests":"NOT_RUN"},indent=2),flush=True)
    return 0
if __name__=="__main__": raise SystemExit(main())