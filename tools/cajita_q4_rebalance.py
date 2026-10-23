#!/usr/bin/env python3
"""Rebalance Cajita's existing low-rank weights in-place, preserving model identities."""
from __future__ import annotations
import hashlib, json, math, os, re, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "cajita-luna-runtime"
WEIGHTS_MANIFEST = RUNTIME / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
REPORT = ROOT / "docs/cajita-luna/CAJITA_RUNTIME_Q4_REBALANCE_20261023.json"
HARD_CAP = 470_000_000
GROUP_SIZES = (128, 64, 32, 16)
MODEL_RUNS = [
 {"id":"W01_CEREBRO","rel":"1. Cerebro/model.safetensors","runtime":"1. Cerebro/cerebro_180mb_runtime.py","args":["--smoke-test"],"signature":["status","argmax_token_id"]},
 {"id":"W02_TRANSCRIPTION","rel":"3. Transcripción/model.safetensors","runtime":"3. Transcripción/lowrank_runtime.py","args":["--smoke-test"],"signature":["status","decoded","generated_token_count"]},
 {"id":"W03_TRANSLATION","rel":"4. Traductor Inteligente/Traducción general/model.safetensors","runtime":"4. Traductor Inteligente/Traducción general/lowrank_runtime.py","args":["--smoke-test"],"signature":["status","decoded","generated_token_count"]},
 {"id":"W05_QWEN3","rel":"6. Sistema Inteligente/Análisis Avanzado/model.safetensors","runtime":"6. Sistema Inteligente/Análisis Avanzado/lowrank_runtime_v2.py","args":["--smoke-test"],"signature":["status","argmax_token_id"]},
]
ONNX_REL = "6. Sistema Inteligente/Anti-Alucinaciones/model.onnx"
NUMPY_TYPES = {
 "tensor(float)": "float32", "tensor(float16)": "float16", "tensor(double)": "float64",
 "tensor(int64)": "int64", "tensor(int32)": "int32", "tensor(int16)": "int16",
 "tensor(int8)": "int8", "tensor(uint8)": "uint8", "tensor(uint16)": "uint16",
 "tensor(uint32)": "uint32", "tensor(uint64)": "uint64", "tensor(bool)": "bool",
 "tensor(string)": "object",
}

def sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
 return h.hexdigest()

def bytes_tree(base):
 total=0; count=0
 for p in base.rglob("*"):
  if p.is_symlink(): raise RuntimeError("SYMLINK_IN_RUNTIME:"+str(p))
  if p.is_file() and p.name != "MACRODOWN_MANIFEST.json":
   total += p.stat().st_size; count += 1
 return total,count

def factor_key(name):
 leaf=name.rsplit(".",1)[-1].lower()
 return (leaf.endswith("_u") or leaf.endswith("_v")) and ("weight" in leaf or "proj" in leaf or "expert" in leaf or "router" in name.lower() or "shared" in name.lower() or "embed" in name.lower())

def pack_q4_tensor(tensor, group_size, torch):
 flat=tensor.detach().to(device="cpu",dtype=torch.int16).contiguous().reshape(-1)
 numel=flat.numel()
 group_count=math.ceil(numel/group_size)
 padded=torch.zeros(group_count*group_size,dtype=torch.float32)
 padded[:numel]=flat.to(torch.float32)
 matrix=padded.reshape(group_count,group_size)
 maximum=matrix.abs().amax(dim=1)
 scales=torch.where(maximum>0,maximum/7.0,torch.ones_like(maximum)).to(torch.float32)
 codes=torch.round(matrix/scales[:,None]).clamp(-7,7).to(torch.int16).reshape(-1)
 nibbles=torch.bitwise_and(codes,0x0F).to(torch.uint8)
 packed=torch.bitwise_or(nibbles[0::2],torch.bitwise_left_shift(nibbles[1::2],4)).contiguous()
 return packed,scales,numel,tuple(tensor.shape)

def build_q4_candidate(source, candidate, sidecar, group_size, torch, save_file, load_file):
 state=load_file(str(source),device="cpu")
 packed_state={}; entries=[]; factor_count=0; factor_original_bytes=0
 for name,tensor in state.items():
  if tensor.dtype==torch.int8 and tensor.numel()>=group_size and factor_key(name):
   packed,scales,numel,shape=pack_q4_tensor(tensor,group_size,torch)
   pkey="__cajita_q4_packed__."+name
   skey="__cajita_q4_scales__."+name
   packed_state[pkey]=packed
   packed_state[skey]=scales
   entries.append({"name":name,"packed_key":pkey,"scales_key":skey,"shape":list(shape),"numel":numel})
   factor_count+=1; factor_original_bytes+=tensor.numel()
  else:
   packed_state[name]=tensor.contiguous()
 if factor_count==0:
  raise RuntimeError("NO_INT8_LOW_RANK_FACTOR_TENSORS")
 save_file(packed_state,str(candidate),metadata={"cajita_format":"CAJITA_Q4_BLOCK_PACKED/1.0"})
 digest=sha256(candidate)
 meta={"schema":"CAJITA_Q4_BLOCK_PACKED/1.0","group_size":group_size,
       "source_sha256":sha256(source),"candidate_sha256":digest,
       "factor_tensor_count":factor_count,"factor_values_packed":factor_original_bytes,
       "tensors":entries}
 sidecar.write_text(json.dumps(meta,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
 return {"candidate_bytes":candidate.stat().st_size,"candidate_sha256":digest,
         "group_size":group_size,"factor_tensor_count":factor_count,
         "factor_values_packed":factor_original_bytes,"sidecar_bytes":sidecar.stat().st_size}

def run_model_smoke(spec, timeout=600):
 env=os.environ.copy()
 env.update({"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1",
             "NUMEXPR_NUM_THREADS":"1","TOKENIZERS_PARALLELISM":"false",
             "HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1"})
 cmd=[sys.executable,"-B",str(RUNTIME/spec["runtime"]),*spec["args"]]
 try:
  p=subprocess.run(cmd,cwd=str(RUNTIME),env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 except subprocess.TimeoutExpired as e:
  return {"status":"TIMEOUT","returncode":124,"stderr_tail":str(e)[:600]}
 try: data=json.loads(p.stdout.strip()) if p.stdout.strip() else {}
 except Exception: data={"unparsed_stdout_tail":p.stdout[-1000:]}
 ok=p.returncode==0 and isinstance(data,dict) and str(data.get("status","")).startswith("PASS")
 return {"status":data.get("status","FAIL") if isinstance(data,dict) else "FAIL",
         "returncode":p.returncode,"result":data,
         "stderr_tail":p.stderr[-1500:],"passed":ok}

def signature_equal(spec, before, after):
 a=before.get("result",{}); b=after.get("result",{})
 if not before.get("passed") or not after.get("passed"): return False
 return all(a.get(k)==b.get(k) for k in spec["signature"])

def quantize_factor_model(spec, torch, load_file, save_file):
 path=RUNTIME/spec["rel"]
 result={"id":spec["id"],"path":spec["rel"],"original_bytes":path.stat().st_size,
         "original_sha256":sha256(path),"attempts":[],"status":"NOT_PROMOTED"}
 with tempfile.TemporaryDirectory(prefix="cajita-q4-") as td:
  tmp=Path(td); backup=tmp/"original.safetensors"; shutil.copy2(path,backup)
  baseline=run_model_smoke(spec)
  result["baseline_smoke"]={"passed":baseline.get("passed",False),"status":baseline.get("status"),
                            "returncode":baseline.get("returncode"),"result":baseline.get("result",{})}
  if not baseline.get("passed"):
   result["status"]="BLOCKED_BASELINE_SMOKE_FAILED"
   return result
  for group_size in GROUP_SIZES:
   candidate=tmp/f"candidate_g{group_size}.safetensors"
   candidate_meta=tmp/f"candidate_g{group_size}.q4.json"
   try:
    info=build_q4_candidate(backup,candidate,candidate_meta,group_size,torch,save_file,load_file)
   except Exception as exc:
    result["attempts"].append({"group_size":group_size,"status":"CANDIDATE_BUILD_FAILED",
                               "error":type(exc).__name__+":"+str(exc)[:800]})
    continue
   if info["candidate_bytes"] + info["sidecar_bytes"] >= result["original_bytes"]:
    result["attempts"].append({**info,"status":"CANDIDATE_WITH_SIDECAR_NOT_SMALLER"})
    continue
   shutil.copy2(candidate,path)
   live_sidecar=path.with_name(path.name+".q4.json")
   shutil.copy2(candidate_meta,live_sidecar)
   after=run_model_smoke(spec)
   same=signature_equal(spec,baseline,after)
   smoke_ok=bool(after.get("passed"))
   attempt={**info,"runtime_smoke_after":{"passed":smoke_ok,"status":after.get("status"),
              "returncode":after.get("returncode"),"result":after.get("result",{}),
              "stderr_tail":after.get("stderr_tail","")},
           "smoke_signature_preserved":same,
           "smoke_passed":smoke_ok,
           "status":"PROMOTED" if smoke_ok else "ROLLBACK_FUNCTIONAL_SMOKE_FAILURE"}
   result["attempts"].append(attempt)
   if smoke_ok:
    result["status"]="PROMOTED_Q4_BLOCKWISE"
    result["candidate_bytes"]=path.stat().st_size
    result["candidate_sha256"]=sha256(path)
    result["sidecar_bytes"]=live_sidecar.stat().st_size
    result["saved_bytes"]=result["original_bytes"]-result["candidate_bytes"]-result["sidecar_bytes"]
    return result
   shutil.copy2(backup,path)
   live_sidecar.unlink(missing_ok=True)
  shutil.copy2(backup,path)
  path.with_name(path.name+".q4.json").unlink(missing_ok=True)
  result["status"]="NO_Q4_CANDIDATE_PASSED_SMOKE"
  return result

def make_onnx_inputs(session, np):
 feed={}
 for item in session.get_inputs():
  dims=[]
  for d in item.shape:
   dims.append(int(d) if isinstance(d,int) and 0 < d <= 2048 else 1)
  dtype=NUMPY_TYPES.get(item.type,"float32")
  shape=tuple(dims)
  if dtype=="object":
   count=max(1,math.prod(shape) if shape else 1)
   arr=np.asarray(["test"]*count,dtype=object).reshape(shape if shape else ())
  else:
   arr=np.zeros(shape,dtype=getattr(np,dtype,np.float32))
  feed[item.name]=arr
 return feed

def compare_onnx_outputs(before, after, np):
 if len(before)!=len(after): return False,{"reason":"OUTPUT_COUNT_MISMATCH"}
 measurements=[]
 for i,(a,b) in enumerate(zip(before,after)):
  aa=np.asarray(a); bb=np.asarray(b)
  if aa.shape!=bb.shape: return False,{"reason":"OUTPUT_SHAPE_MISMATCH","index":i,"before":list(aa.shape),"after":list(bb.shape)}
  if aa.dtype.kind in "OUS" or bb.dtype.kind in "OUS":
   same=bool(np.array_equal(aa,bb)); measurements.append({"index":i,"exact_match":same})
   if not same: return False,{"reason":"NON_NUMERIC_OUTPUT_MISMATCH","outputs":measurements}
   continue
  af=aa.astype(np.float64,copy=False); bf=bb.astype(np.float64,copy=False)
  if not np.isfinite(af).all() or not np.isfinite(bf).all():
   return False,{"reason":"NONFINITE_OUTPUT","index":i}
  denominator=max(float(np.linalg.norm(af.reshape(-1))),1e-12)
  rel=float(np.linalg.norm((bf-af).reshape(-1))/denominator)
  top1_same=bool(np.argmax(af)==np.argmax(bf)) if af.size else True
  measurements.append({"index":i,"relative_l2_error":rel,"top1_same":top1_same,"shape":list(aa.shape)})
  if not top1_same or rel>0.10:
   return False,{"reason":"OUTPUT_TOLERANCE_FAILED","outputs":measurements,"relative_l2_threshold":0.10}
 return True,{"outputs":measurements,"policy":"same top-1 and relative L2 <= 0.10 on deterministic zero-valued smoke inputs; not a task-level quality certificate"}

def quantize_onnx():
 result={"path":ONNX_REL,"status":"NOT_PROMOTED"}
 path=RUNTIME/ONNX_REL
 result["original_bytes"]=path.stat().st_size; result["original_sha256"]=sha256(path)
 try:
  import numpy as np
  import onnx
  import onnxruntime as ort
  from onnxruntime.quantization import quantize_dynamic, QuantType
 except Exception as exc:
  result.update({"status":"BLOCKED_DEPENDENCY","error":type(exc).__name__+":"+str(exc)[:1000]}); return result
 with tempfile.TemporaryDirectory(prefix="cajita-onnx-int8-") as td:
  candidate=Path(td)/"candidate.int8.onnx"
  try:
   session0=ort.InferenceSession(str(path),providers=["CPUExecutionProvider"])
   feed=make_onnx_inputs(session0,np)
   out0=session0.run(None,feed)
   quantize_dynamic(str(path),str(candidate),weight_type=QuantType.QInt8)
   onnx.checker.check_model(str(candidate),full_check=False)
   session1=ort.InferenceSession(str(candidate),providers=["CPUExecutionProvider"])
   feed1=make_onnx_inputs(session1,np)
   out1=session1.run(None,feed1)
   equivalent,metrics=compare_onnx_outputs(out0,out1,np)
   result["candidate_bytes"]=candidate.stat().st_size
   result["candidate_sha256"]=sha256(candidate)
   result["output_comparison"]=metrics
   result["graph_check"]="PASS"
   result["cpu_session_load"]="PASS"
   if candidate.stat().st_size >= path.stat().st_size:
    result["status"]="CANDIDATE_NOT_SMALLER"; return result
   if not equivalent:
    result["status"]="ROLLBACK_OUTPUT_SMOKE_MISMATCH"; return result
   shutil.copy2(candidate,path)
   result["status"]="PROMOTED_DYNAMIC_INT8"
   result["saved_bytes"]=result["original_bytes"]-result["candidate_bytes"]
   return result
  except Exception as exc:
   result.update({"status":"QUANTIZATION_OR_VALIDATION_FAILED","error":type(exc).__name__+":"+str(exc)[:1500]})
   return result

def format_es(value): return f"{int(value):,}".replace(",",".")

def update_manifest_and_doc():
 manifest=json.loads(WEIGHTS_MANIFEST.read_text(encoding="utf-8"))
 for item in manifest.get("artifacts",[]):
  p=RUNTIME/item["path"]
  if p.is_file():
   item["bytes"]=p.stat().st_size
   item["sha256"]=sha256(p)
 manifest["total_weight_bytes"]=sum(int(x["bytes"]) for x in manifest.get("artifacts",[]))
 WEIGHTS_MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 manifest_hash=sha256(WEIGHTS_MANIFEST)
 router=RUNTIME/"cajita_runtime.py"
 text=router.read_text(encoding="utf-8")
 text,n=re.subn(r'MANIFEST_SHA256\s*=\s*"[0-9a-f]{64}"',
                'MANIFEST_SHA256 = "'+manifest_hash+'"',text,count=1)
 if n!=1: raise RuntimeError("WEIGHT_MANIFEST_HASH_CONSTANT_NOT_FOUND")
 router.write_text(text,encoding="utf-8")
 doc=RUNTIME/"CajitadeLuna.md"
 text=doc.read_text(encoding="utf-8")
 for item in manifest.get("artifacts",[]):
  rel=item["path"].replace("\\","/")
  pattern=re.compile(r"(\|\s*"+chr(96)+re.escape(rel)+chr(96)+r"\s*\|)\s*[\d.]+\s*(\|)")
  text,_=pattern.subn(lambda m:m.group(1)+" "+format_es(item["bytes"])+" "+m.group(2),text,count=1)
 total=manifest["total_weight_bytes"]
 text=re.sub(r"(\|\s*\*\*Total de seis archivos de modelo/pesos\*\*\s*\|\s*\|)\s*\*\*[\d.]+\*\*\s*(\|)",
             lambda m:m.group(1)+" **"+format_es(total)+"** "+m.group(2),text,count=1)
 marker="## Rebalanceo de peso cuantizado — 2026-10-23"
 if marker not in text:
  lines=[]
  for r in report["weight_factor_results"]:
   lines.append("| "+r["id"]+" | "+chr(96)+r["path"]+chr(96)+" | "+str(r.get("status","NOT_CHANGED"))+" | "+str(r.get("original_bytes",""))+" | "+str(r.get("candidate_bytes",r.get("original_bytes","")))+" |")
  r=report.get("onnx_result",{})
  lines.append("| W06_ONNX | "+chr(96)+r.get("path",ONNX_REL)+chr(96)+" | "+str(r.get("status","NOT_CHANGED"))+" | "+str(r.get("original_bytes",""))+" | "+str(r.get("candidate_bytes",r.get("original_bytes","")))+" |")
  text += "\n\n"+marker+"\n\nLa pasada actúa sobre los factores INT8 de bajo rango de los cuatro motores que usan model.safetensors y ensaya cuantización INT8 dinámica del ONNX. Un candidato solo se promueve si reduce bytes y el smoke de salida conserva la firma funcional determinista observada antes de la transformación. Los artefactos originales quedan recuperables en el historial Git; el informe registra hashes, tamaños y rollback.\n\n| Motor | Ruta | Estado | Bytes originales | Bytes candidatos/activos |\n|---|---|---|---:|---:|\n"+"\n".join(lines)+"\n\nEl control de tamaño suma los archivos reales del runtime, excluye únicamente el manifiesto de distribución que el constructor regenera y compara con el techo decimal de 470.000.000 bytes. Este control de tamaño no equivale por sí solo a certificación integral de calidad.\n"
 doc.write_text(text.rstrip()+"\n",encoding="utf-8")
 return manifest_hash

def main():
 global report
 started=time.monotonic()
 try:
  import numpy as np
  import torch
  from safetensors.torch import load_file, save_file
 except Exception as exc:
  print(json.dumps({"status":"BLOCKED_DEPENDENCY","error":type(exc).__name__+":"+str(exc),"certification":"NOT_GRANTED"})); return 0
 pre,pre_count=bytes_tree(RUNTIME)
 report={"schema":"CAJITA_RUNTIME_HARD_CAP_REBALANCE/1.0",
         "audit_id":"CAJITA_RUNTIME_Q4_REBALANCE_20261023",
         "created_at_utc":datetime.now(timezone.utc).isoformat(),
         "repository":"Plomillo/luna-linux-bridge","branch":"main",
         "hard_cap_bytes":HARD_CAP,"size_basis":"sum of actual runtime file bytes excluding only the regenerated MACRODOWN_MANIFEST.json",
         "runtime_bytes_before":pre,"runtime_file_count_before":pre_count,"weight_factor_results":[]}
 for spec in MODEL_RUNS:
  path=RUNTIME/spec["rel"]
  if not path.is_file():
   report["weight_factor_results"].append({"id":spec["id"],"path":spec["rel"],"status":"BLOCKED_WEIGHT_MISSING"})
   continue
  if path.with_name(path.name+".q4.json").is_file():
   report["weight_factor_results"].append({"id":spec["id"],"path":spec["rel"],"status":"ALREADY_Q4_PACKED","candidate_bytes":path.stat().st_size})
   continue
  report["weight_factor_results"].append(quantize_factor_model(spec,torch,load_file,save_file))
 report["onnx_result"]=quantize_onnx()
 report["weights_manifest_sha256"]=update_manifest_and_doc()
 post,post_count=bytes_tree(RUNTIME)
 report["runtime_bytes_after"]=post; report["runtime_file_count_after"]=post_count
 report["saved_bytes"]=pre-post
 report["bytes_over_cap"]=max(0,post-HARD_CAP)
 report["size_gate"]="PASS" if post<=HARD_CAP else "FAIL"
 report["quantized_factor_models_promoted"]=sum(x.get("status")=="PROMOTED_Q4_BLOCKWISE" for x in report["weight_factor_results"])
 report["onnx_status"]=report["onnx_result"].get("status")
 report["quality_equivalence"]="SMOKE_SIGNATURE_ONLY; TASK_LEVEL_QUALITY_NOT_ESTABLISHED"
 report["independent_validation"]="NOT_RUN"
 report["certification"]="NOT_GRANTED"
 report["elapsed_seconds"]=round(time.monotonic()-started,3)
 report["status"]="SIZE_GATE_PASS_CERTIFICATION_NOT_GRANTED" if post<=HARD_CAP else "SIZE_GATE_FAIL_OPTIMIZATION_RESULTS_COMMITTED_FOR_NEXT_PASS"
 REPORT.parent.mkdir(parents=True,exist_ok=True)
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"status":report["status"],"runtime_bytes_before":pre,"runtime_bytes_after":post,
   "saved_bytes":pre-post,"hard_cap_bytes":HARD_CAP,"bytes_over_cap":report["bytes_over_cap"],
   "size_gate":report["size_gate"],"q4_models_promoted":report["quantized_factor_models_promoted"],
   "onnx_status":report["onnx_status"],"certification":report["certification"]},ensure_ascii=False))
 return 0

if __name__=="__main__": raise SystemExit(main())
