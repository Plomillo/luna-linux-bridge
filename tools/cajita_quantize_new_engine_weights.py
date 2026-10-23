#!/usr/bin/env python3
"""Quantize real ONNX tensors inside the ten new Cajita asset containers.
Never lossy-transform executable bytes, and never touch the six protected legacy weights.
"""
import hashlib, json, os, shutil, subprocess, sys, tarfile, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path.cwd()
PLACEMENT = ROOT / "cajita-luna-runtime/EXTERNALIZED_ASSET_PLACEMENT.json"
REPORT = ROOT / "docs/cajita-luna/CAJITA_NEW_ENGINE_QUANTIZATION_20261023.json"
OUT = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "cajita_quantized_candidates"
MAX_EXPANDED = 1_500_000_000
MAX_DEPTH = 4
MODEL_EXTS = {".onnx", ".safetensors", ".gguf", ".tflite", ".pb", ".pt", ".pth", ".h5", ".hdf5", ".keras"}
ARCHIVE_ENDINGS = (".tar.gz", ".tgz", ".tar", ".zip", ".whl", ".nupkg", ".gz")
PROTECTED = [
 "1. Cerebro/model.safetensors", "3. Transcripción/model.safetensors",
 "4. Traductor Inteligente/Traducción general/model.safetensors",
 "5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_weights.bin",
 "6. Sistema Inteligente/Análisis Avanzado/model.safetensors",
 "6. Sistema Inteligente/Anti-Alucinaciones/model.onnx"
]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
 return h.hexdigest()
def archive(p): return p.name.lower().endswith(ARCHIVE_ENDINGS)
def safe_path(root, name):
 q=PurePosixPath(name)
 if q.is_absolute() or ".." in q.parts: return None
 p=(root/Path(*q.parts)).resolve()
 return p if p==root.resolve() or root.resolve() in p.parents else None
def unpack_nested(src, dst, budget):
 dst.mkdir(parents=True, exist_ok=True); out=[]
 try:
  if zipfile.is_zipfile(src):
   with zipfile.ZipFile(src) as z:
    for i in z.infolist():
     if i.is_dir(): continue
     p=safe_path(dst,i.filename)
     if p is None: continue
     p.parent.mkdir(parents=True,exist_ok=True)
     with z.open(i) as r,p.open("wb") as w:
      while True:
       b=r.read(1024*1024)
       if not b: break
       budget[0]+=len(b)
       if budget[0]>MAX_EXPANDED: raise RuntimeError("expanded-size safety limit")
       w.write(b)
     out.append(p)
  elif tarfile.is_tarfile(src):
   with tarfile.open(src,"r:*") as t:
    for m in t:
     if not m.isfile(): continue
     p=safe_path(dst,m.name)
     if p is None: continue
     r=t.extractfile(m)
     if r is None: continue
     p.parent.mkdir(parents=True,exist_ok=True)
     with r,p.open("wb") as w:
      while True:
       b=r.read(1024*1024)
       if not b: break
       budget[0]+=len(b)
       if budget[0]>MAX_EXPANDED: raise RuntimeError("expanded-size safety limit")
       w.write(b)
     out.append(p)
 except (OSError,tarfile.TarError,zipfile.BadZipFile,RuntimeError):
  return []
 return out
def main():
 if not PLACEMENT.is_file(): raise SystemExit("FAIL_CLOSED: placement manifest absent")
 assets=json.loads(PLACEMENT.read_text(encoding="utf-8")).get("assets",[])
 if len(assets)!=10: raise SystemExit(f"FAIL_CLOSED: expected 10 assets, got {len(assets)}")
 OUT.mkdir(parents=True,exist_ok=True); rows=[]; onnx_models=[]; scanned=0; expanded_total=0
 with tempfile.TemporaryDirectory(prefix="cajita-quantize-") as td:
  tmp=Path(td)
  for a in assets:
   aid=a["id"]; rel=a.get("placed_path",""); src=ROOT/rel
   row={"asset_id":aid,"container_path":rel,"container_exists":src.is_file(),
        "container_bytes":src.stat().st_size if src.is_file() else None,
        "container_sha256":sha(src) if src.is_file() else None,
        "model_payloads_found":[],"quantization_results":[]}
   if not src.is_file() or src.suffix.lower()!=".7z":
    row["status"]="BLOCKED_CONTAINER_MISSING_OR_UNEXPECTED_FORMAT"; rows.append(row); continue
   base=tmp/aid;base.mkdir(parents=True,exist_ok=True)
   proc=subprocess.run(["7z","x","-y",f"-o{base}",str(src)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   if proc.returncode:
    row["status"]="BLOCKED_EXTRACTION_FAILED";row["log_tail"]=proc.stdout[-1500:];rows.append(row);continue
   files=[p for p in base.rglob("*") if p.is_file()]
   seen={p.resolve() for p in files}; budget=[sum(p.stat().st_size for p in files)]
   queue=[(p,0) for p in files if archive(p)]
   while queue and budget[0]<MAX_EXPANDED and len(seen)<50000:
    ar,depth=queue.pop(0)
    if depth>=MAX_DEPTH: continue
    new=unpack_nested(ar,tmp/"nested"/aid/str(len(seen)),budget)
    for p in new:
     rp=p.resolve()
     if rp in seen: continue
     seen.add(rp)
     if archive(p): queue.append((p,depth+1))
   files=[Path(p) for p in seen if Path(p).is_file()]
   scanned+=len(files);expanded_total+=budget[0]
   for f in files:
    n=f.name.lower(); ext=f.suffix.lower()
    if ext not in MODEL_EXTS and n not in {"pytorch_model.bin","model.onnx"}: continue
    item={"name":f.name,"suffix":ext,"bytes":f.stat().st_size,"sha256":sha(f)}
    if ext==".onnx":
     copy=tmp/"onnx"/aid/f"{len(onnx_models):04d}_{f.name}";copy.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,copy)
     onnx_models.append((aid,copy,item["sha256"]));item["quantizer"]="ONNX_DYNAMIC_INT8"
    else:item["quantizer"]="ARCHITECTURE_SPECIFIC_REQUIRED"
    row["model_payloads_found"].append(item)
   row["expanded_bytes_scanned"]=budget[0]
   row["status"]="MODEL_PAYLOADS_FOUND" if row["model_payloads_found"] else "NO_NEURAL_MODEL_PAYLOAD_FOUND"
   rows.append(row)
  if onnx_models:
   deps=OUT.parent/"cajita_quantizer_python_deps"
   p=subprocess.run([sys.executable,"-m","pip","install","--disable-pip-version-check","--upgrade",
     "--target",str(deps),"onnx","onnxruntime"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   if p.returncode:
    for aid,model,h in onnx_models:
     next(r for r in rows if r["asset_id"]==aid)["quantization_results"].append(
      {"source_sha256":h,"status":"BLOCKED_QUANTIZER_INSTALL_FAILED","log_tail":p.stdout[-2500:]})
   else:
    sys.path.insert(0,str(deps))
    try:
     import onnx, onnxruntime as ort
     from onnxruntime.quantization import quantize_dynamic, QuantType
    except Exception as import_error:
     for aid,model,h in onnx:
      next(r for r in rows if r["asset_id"]==aid)["quantization_results"].append(
       {"source_sha256":h,"status":"BLOCKED_QUANTIZER_IMPORT_FAILED",
        "error":f"{type(import_error).__name__}: {import_error}","install_log_tail":p.stdout[-2500:]})
    else:
     for ix,(aid,model,orig_hash) in enumerate(onnx_models):
      target=next(r for r in rows if r["asset_id"]==aid)
      q=OUT/aid/f"{ix:03d}_{model.stem}.int8.onnx";q.parent.mkdir(parents=True,exist_ok=True)
      try:
       onnx.load(str(model),load_external_data=True)
       quantize_dynamic(str(model),str(q),weight_type=QuantType.QInt8)
       onnx.checker.check_model(str(q),full_check=False)
       sess=ort.InferenceSession(str(q),providers=["CPUExecutionProvider"])
       before,after=model.stat().st_size,q.stat().st_size
       target["quantization_results"].append({
        "source_sha256":orig_hash,"candidate_artifact_path":str(q.relative_to(OUT.parent)),
        "candidate_sha256":sha(q),"original_bytes":before,"candidate_bytes":after,
        "saved_bytes":before-after,"quantization":"ONNX_DYNAMIC_INT8",
        "graph_check":"PASS","cpu_session_load":"PASS",
        "inputs":[v.name for v in sess.get_inputs()],"outputs":[v.name for v in sess.get_outputs()],
        "status":"QUANTIZED_CANDIDATE_SMALLER" if after<before else "QUANTIZED_CANDIDATE_NOT_SMALLER",
        "runtime_replacement":"NOT_PROMOTED_WITHOUT_GOLDEN_EQUIVALENCE_TESTS"})
      except Exception as e:
       if q.exists():q.unlink()
       target["quantization_results"].append({"source_sha256":orig_hash,
        "quantization":"ONNX_DYNAMIC_INT8","status":"QUANTIZATION_OR_VALIDATION_FAILED",
        "error":f"{type(e).__name__}: {e}"[:1500]})
 models=sum(len(r["model_payloads_found"]) for r in rows)
 wins=sum(q.get("status")=="QUANTIZED_CANDIDATE_SMALLER" for r in rows for q in r["quantization_results"])
 report={"schema":"CAJITA_NEW_ENGINE_MODEL_QUANTIZATION/1.0","audit_id":"CAJITA_NEW_ENGINE_QUANTIZATION_20261023",
  "created_at_utc":datetime.now(timezone.utc).isoformat(),"repository":"Plomillo/luna-linux-bridge","branch":"main",
  "target_hard_cap_bytes":470000000,"scope":"exactly ten newly incorporated assets in EXTERNALIZED_ASSET_PLACEMENT.json",
  "method":"Scan nested containers and dynamically quantize actual ONNX graphs to signed INT8; never lossy-transform general executable bytes.",
  "protected_legacy_weights":{"policy":"NO_MODIFICATION","paths":PROTECTED,"status":"NOT_TARGETED"},
  "summary":{"assets_expected":10,"assets_scanned":len(rows),"files_scanned":scanned,"expanded_bytes_scanned":expanded_total,
   "model_payloads_found":models,"onnx_candidates_quantized_smaller_and_validated":wins,
   "hard_cap_compliance":"NOT_EVALUATED_BY_QUANTIZATION_PASS",
   "status":"QUANTIZED_CANDIDATES_CREATED" if wins else "NO_ONNX_TENSORS_FOUND_IN_THE_TEN_ASSETS"},
  "assets":rows,"caveats":["Model file types other than ONNX are inventoried but require architecture-specific quantizers.",
   "Graph validation and CPU session loading are not quality equivalence tests; candidates are not auto-promoted.",
   "Six prior legacy model paths are not touched."]}
 REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(report["summary"],ensure_ascii=False))
 return 2 if any(r.get("status","").startswith("BLOCKED") for r in rows) else 0
if __name__=="__main__": raise SystemExit(main())
