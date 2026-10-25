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
 codes=torch.round(matrix/scales[:,None]).clamp(-7,7).to(torch.int16).reshape(-1)[:numel]
 nibbles=torch.bitwise_and(codes,0x0F).to(torch.uint8)
 if nibbles.numel() % 2:
  nibbles=torch.cat((nibbles,torch.zeros(1,dtype=torch.uint8)))
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
 result={"path":ONNX_REL,"status":"NOT_PROMOTED","attempts":[]}
 path=RUNTIME/ONNX_REL
 result["original_bytes"]=path.stat().st_size; result["original_sha256"]=sha256(path)
 try:
  import numpy as np
  import onnx
  import onnxruntime as ort
  from onnxruntime.quantization import quantize_dynamic, QuantType
 except Exception as exc:
  result.update({"status":"BLOCKED_DEPENDENCY","error":type(exc).__name__+":"+str(exc)[:1000]}); return result
 with tempfile.TemporaryDirectory(prefix="cajita-onnx-rebalance-") as td:
  tmp=Path(td)
  try:
   source_model=onnx.load(str(path),load_external_data=True)
   onnx.checker.check_model(source_model,full_check=False)
   used=set()
   op_counts={}
   def scan_graph(graph):
    for node in graph.node:
     op_counts[node.op_type]=op_counts.get(node.op_type,0)+1
     used.update(node.input)
     for attr in node.attribute:
      if attr.type==onnx.AttributeProto.GRAPH:
       scan_graph(attr.g)
      elif attr.type==onnx.AttributeProto.GRAPHS:
       for sub in attr.graphs: scan_graph(sub)
   scan_graph(source_model.graph)
   dtype_bytes={}; initializer_total=0; unused_bytes=0; unused_names=[]
   for tensor in source_model.graph.initializer:
    if tensor.data_location==onnx.TensorProto.EXTERNAL:
     size=int(next((e.value for e in tensor.external_data if e.key=="length"),"0"))
    else:
     try: size=len(tensor.raw_data) if tensor.raw_data else int(onnx.numpy_helper.to_array(tensor).nbytes)
     except Exception: size=0
    dtype=onnx.TensorProto.DataType.Name(tensor.data_type)
    dtype_bytes[dtype]=dtype_bytes.get(dtype,0)+size
    initializer_total+=size
    if tensor.name not in used:
     unused_bytes+=size; unused_names.append({"name":tensor.name,"bytes":size,"dtype":dtype})
   result["graph_profile"]={"node_count":len(source_model.graph.node),"op_type_counts":op_counts,
       "initializer_count":len(source_model.graph.initializer),"initializer_payload_bytes":initializer_total,
       "initializer_bytes_by_dtype":dtype_bytes,"unused_initializer_bytes":unused_bytes,
       "unused_initializer_count":len(unused_names),"unused_initializer_preview":unused_names[:30]}
   session0=ort.InferenceSession(str(path),providers=["CPUExecutionProvider"])
   feed0=make_onnx_inputs(session0,np)
   out0=session0.run(None,feed0)
  except Exception as exc:
   result.update({"status":"SOURCE_MODEL_LOAD_OR_PROFILE_FAILED","error":type(exc).__name__+":"+str(exc)[:1500]})
   return result
  candidates=[]
  dynamic=tmp/"candidate.dynamic-int8.onnx"
  try:
   quantize_dynamic(str(path),str(dynamic),weight_type=QuantType.QInt8)
   if dynamic.is_file():
    candidates.append({"method":"ONNX_DYNAMIC_INT8","path":dynamic})
  except Exception as exc:
   result["attempts"].append({"method":"ONNX_DYNAMIC_INT8","status":"CANDIDATE_BUILD_FAILED",
                              "error":type(exc).__name__+":"+str(exc)[:1200]})
  fp16=tmp/"candidate.float16.onnx"
  try:
   from onnxconverter_common import float16 as onnx_float16
   model_fp16=onnx_float16.convert_float_to_float16(source_model,keep_io_types=True,disable_shape_infer=True)
   onnx.save_model(model_fp16,str(fp16))
   candidates.append({"method":"ONNX_FLOAT16_CONVERSION","path":fp16})
  except Exception as exc:
   result["attempts"].append({"method":"ONNX_FLOAT16_CONVERSION","status":"CANDIDATE_BUILD_FAILED",
                              "error":type(exc).__name__+":"+str(exc)[:1500]})
  for candidate in candidates:
   cp=candidate["path"]; method=candidate["method"]
   attempt={"method":method,"candidate_bytes":cp.stat().st_size,"candidate_sha256":sha256(cp)}
   try:
    onnx.checker.check_model(str(cp),full_check=False)
    sess=ort.InferenceSession(str(cp),providers=["CPUExecutionProvider"])
    feed=make_onnx_inputs(sess,np)
    outputs=sess.run(None,feed)
    equivalent,metrics=compare_onnx_outputs(out0,outputs,np)
    attempt.update({"graph_check":"PASS","cpu_session_load":"PASS","output_comparison":metrics,
                    "output_smoke_passed":equivalent})
   except Exception as exc:
    attempt.update({"graph_or_runtime_check":"FAIL","error":type(exc).__name__+":"+str(exc)[:1500],
                    "status":"CANDIDATE_RUNTIME_FAILED"})
    result["attempts"].append(attempt)
    continue
   if cp.stat().st_size>=path.stat().st_size:
    attempt["status"]="CANDIDATE_NOT_SMALLER"
    result["attempts"].append(attempt)
    continue
   if not equivalent:
    attempt["status"]="CANDIDATE_OUTPUT_MISMATCH"
    result["attempts"].append(attempt)
    continue
   shutil.copy2(cp,path)
   attempt["status"]="PROMOTED"
   result["attempts"].append(attempt)
   result.update({"status":"PROMOTED_"+method,"candidate_bytes":path.stat().st_size,
                  "candidate_sha256":sha256(path),
                  "saved_bytes":result["original_bytes"]-path.stat().st_size,
                  "output_comparison":metrics,"graph_check":"PASS","cpu_session_load":"PASS"})
   return result
  if any(a.get("status")=="CANDIDATE_NOT_SMALLER" for a in result["attempts"]):
   result["status"]="CANDIDATES_NOT_SMALLER_OR_FAILED_VALIDATION"
  else:
   result["status"]="NO_SMALLER_VALIDATED_CANDIDATE"
  # Normalize scratch paths in recorded exception text. TemporaryDirectory names
  # are random; retaining them creates a new report/main commit on every no-op run.
  temp_prefix = str(tmp)
  def stable_temp_paths(value):
   if isinstance(value, str):
    return value.replace(temp_prefix, "<ONNX_TEMP_DIR>")
   if isinstance(value, list):
    return [stable_temp_paths(item) for item in value]
   if isinstance(value, dict):
    return {key: stable_temp_paths(item) for key, item in value.items()}
   return value
  result = stable_temp_paths(result)
  return result

def pack_q2_affine_tensor(tensor, group_size, torch):
 flat=tensor.detach().to(device="cpu",dtype=torch.float32).contiguous().reshape(-1)
 numel=flat.numel()
 groups=math.ceil(numel/group_size)
 padded=torch.zeros(groups*group_size,dtype=torch.float32)
 padded[:numel]=flat
 matrix=padded.reshape(groups,group_size)
 minima=matrix.amin(dim=1)
 maxima=matrix.amax(dim=1)
 steps=(maxima-minima)/3.0
 steps=torch.where(steps>0,steps,torch.ones_like(steps)).to(torch.float32)
 codes=torch.round((matrix-minima[:,None])/steps[:,None]).clamp(0,3).to(torch.uint8).reshape(-1)[:numel]
 if codes.numel()%4:
  codes=torch.cat((codes,torch.zeros(4-codes.numel()%4,dtype=torch.uint8)))
 packed=torch.bitwise_or(
  torch.bitwise_or(codes[0::4],torch.bitwise_left_shift(codes[1::4],2)),
  torch.bitwise_or(torch.bitwise_left_shift(codes[2::4],4),torch.bitwise_left_shift(codes[3::4],6))
 ).contiguous()
 return packed,minima,steps,numel,tuple(tensor.shape)

def quantize_factor_models_q2(torch, load_file, save_file):
 """Second-stage asymmetric 2-bit packing for the existing Q4 low-rank factor tensors."""
 if str(RUNTIME) not in sys.path:
  sys.path.insert(0,str(RUNTIME))
 from cajita_weight_materializer import load_model_state
 rows=[]
 for spec in MODEL_RUNS:
  path=RUNTIME/spec["rel"]
  sidecar=path.with_name(path.name+".q4.json")
  row={"id":spec["id"],"path":spec["rel"],"status":"NOT_PROMOTED"}
  if not path.is_file() or not sidecar.is_file():
   row["status"]="SKIPPED_NO_Q4_SIDECAR"; rows.append(row); continue
  current_meta=json.loads(sidecar.read_text(encoding="utf-8"))
  entries=current_meta.get("tensors",[])
  if not entries:
   row["status"]="SKIPPED_NO_FACTOR_ENTRIES"; rows.append(row); continue
  if all(e.get("encoding")=="UNSIGNED_INT2_ASYMMETRIC" for e in entries):
   row["status"]="ALREADY_Q2_PACKED"; row["candidate_bytes"]=path.stat().st_size; rows.append(row); continue
  if any(e.get("encoding")=="UNSIGNED_INT2_ASYMMETRIC" for e in entries):
   row["status"]="BLOCKED_PARTIAL_Q2_METADATA"; rows.append(row); continue
  original_bytes=path.stat().st_size
  original_sidecar_bytes=sidecar.stat().st_size
  original_hash=sha256(path)
  baseline=run_model_smoke(spec)
  row.update({"original_bytes":original_bytes,"original_sidecar_bytes":original_sidecar_bytes,
              "original_sha256":original_hash,"factor_tensor_count":len(entries),"attempts":[]})
  row["baseline_smoke"]={"passed":baseline.get("passed",False),"status":baseline.get("status"),
                         "returncode":baseline.get("returncode"),"result":baseline.get("result",{})}
  if not baseline.get("passed"):
   row["status"]="BLOCKED_BASELINE_SMOKE_FAILED"; rows.append(row); continue
  with tempfile.TemporaryDirectory(prefix="cajita-q2-factor-") as td:
   tmp=Path(td)
   backup=tmp/"before.safetensors"; backup_meta=tmp/"before.q4.json"
   shutil.copy2(path,backup); shutil.copy2(sidecar,backup_meta)
   raw_state=load_file(str(backup),device="cpu")
   logical_state=load_model_state(path)
   promoted=False
   for group_size in (512,256,128):
    candidate=tmp/f"candidate_g{group_size}.safetensors"
    candidate_sidecar=tmp/f"candidate_g{group_size}.q4.json"
    candidate_state=dict(raw_state)
    updated_meta=json.loads(json.dumps(current_meta))
    new_entries=[]
    try:
     for entry in updated_meta["tensors"]:
      name=entry["name"]
      if name not in logical_state:
       raise RuntimeError("LOGICAL_FACTOR_NOT_MATERIALIZED:"+name)
      packed_key=entry["packed_key"]; scales_key=entry["scales_key"]
      if packed_key not in candidate_state or scales_key not in candidate_state:
       raise RuntimeError("Q4_SOURCE_KEYS_MISSING:"+name)
      packed,mins,steps,numel,shape=pack_q2_affine_tensor(logical_state[name],group_size,torch)
      min_key="__cajita_q2_min__."+name
      step_key="__cajita_q2_step__."+name
      q2_key="__cajita_q2_packed__."+name
      candidate_state.pop(packed_key); candidate_state.pop(scales_key)
      candidate_state[q2_key]=packed; candidate_state[min_key]=mins; candidate_state[step_key]=steps
      entry.pop("scales_key",None)
      entry.update({"packed_key":q2_key,"min_key":min_key,"step_key":step_key,
                    "group_size":group_size,"original_dtype":"float32",
                    "encoding":"UNSIGNED_INT2_ASYMMETRIC"})
      new_entries.append({"name":name,"numel":numel,"shape":list(shape)})
     save_file(candidate_state,str(candidate),metadata={"cajita_format":"CAJITA_MIXED_BLOCK_PACKED/1.0"})
     candidate_hash=sha256(candidate)
     updated_meta["schema"]="CAJITA_MIXED_BLOCK_PACKED/1.0"
     updated_meta["candidate_sha256"]=candidate_hash
     updated_meta["q2_factor_pass"]={"group_size":group_size,"source_q4_sha256":original_hash,
                                     "packed_tensor_count":len(new_entries),
                                     "packing":"unsigned affine 2-bit codes; per-block min/step FP32"}
     candidate_sidecar.write_text(json.dumps(updated_meta,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    except Exception as exc:
     row["attempts"].append({"group_size":group_size,"status":"CANDIDATE_BUILD_FAILED",
                             "error":type(exc).__name__+":"+str(exc)[:1000]})
     continue
    candidate_total=candidate.stat().st_size+candidate_sidecar.stat().st_size
    original_total=original_bytes+original_sidecar_bytes
    if candidate_total>=original_total:
     row["attempts"].append({"group_size":group_size,"status":"CANDIDATE_WITH_SIDECAR_NOT_SMALLER",
                             "candidate_bytes":candidate.stat().st_size,
                             "candidate_sidecar_bytes":candidate_sidecar.stat().st_size})
     continue
    shutil.copy2(candidate,path); shutil.copy2(candidate_sidecar,sidecar)
    after=run_model_smoke(spec); smoke_ok=bool(after.get("passed"))
    attempt={"group_size":group_size,"candidate_bytes":path.stat().st_size,
             "candidate_sidecar_bytes":sidecar.stat().st_size,"candidate_sha256":sha256(path),
             "candidate_factor_count":len(new_entries),
             "runtime_smoke_after":{"passed":smoke_ok,"status":after.get("status"),
                "returncode":after.get("returncode"),"result":after.get("result",{}),
                "stderr_tail":after.get("stderr_tail","")},
             "status":"PROMOTED" if smoke_ok else "ROLLBACK_RUNTIME_SMOKE_FAILURE"}
    row["attempts"].append(attempt)
    if smoke_ok:
     row.update({"status":"PROMOTED_Q2_BLOCKWISE","group_size":group_size,
                 "candidate_bytes":path.stat().st_size,"candidate_sidecar_bytes":sidecar.stat().st_size,
                 "candidate_sha256":sha256(path),"saved_bytes":original_total-(path.stat().st_size+sidecar.stat().st_size),
                 "smoke_signature_preserved":signature_equal(spec,baseline,after)})
     promoted=True; break
    shutil.copy2(backup,path); shutil.copy2(backup_meta,sidecar)
   if not promoted:
    shutil.copy2(backup,path); shutil.copy2(backup_meta,sidecar)
    row["status"]="NO_Q2_CANDIDATE_PASSED_RUNTIME_SMOKE"
  rows.append(row)
 return rows

def pack_float_tensor(tensor, group_size, torch):
 flat=tensor.detach().to(device="cpu",dtype=torch.float32).contiguous().reshape(-1)
 numel=flat.numel()
 group_count=math.ceil(numel/group_size)
 padded=torch.zeros(group_count*group_size,dtype=torch.float32)
 padded[:numel]=flat
 matrix=padded.reshape(group_count,group_size)
 maximum=matrix.abs().amax(dim=1)
 scales=torch.where(maximum>0,maximum/7.0,torch.ones_like(maximum)).to(torch.float32)
 codes=torch.round(matrix/scales[:,None]).clamp(-7,7).to(torch.int16).reshape(-1)[:numel]
 nibbles=torch.bitwise_and(codes,0x0F).to(torch.uint8)
 if nibbles.numel() % 2:
  nibbles=torch.cat((nibbles,torch.zeros(1,dtype=torch.uint8)))
 packed=torch.bitwise_or(nibbles[0::2],torch.bitwise_left_shift(nibbles[1::2],4)).contiguous()
 return packed,scales,numel,tuple(tensor.shape)

def quantize_remaining_float_tensors(torch, load_file, save_file):
 """Pack the large remaining float tensors in active low-rank models as signed INT4."""
 rows=[]
 for spec in MODEL_RUNS:
  path=RUNTIME/spec["rel"]
  sidecar=path.with_name(path.name+".q4.json")
  if not path.is_file() or not sidecar.is_file():
   rows.append({"id":spec["id"],"path":spec["rel"],"status":"SKIPPED_NO_Q4_SIDECAR"})
   continue
  original_bytes=path.stat().st_size
  original_hash=sha256(path)
  current_meta=json.loads(sidecar.read_text(encoding="utf-8"))
  existing_entries=current_meta.get("tensors",[])+current_meta.get("additional_tensors",[])
  already_packed={x["name"] for x in existing_entries}
  with tempfile.TemporaryDirectory(prefix="cajita-q4-float-") as td:
   tmp=Path(td)
   state=load_file(str(path),device="cpu")
   eligible=[]; dtype_bytes={}
   for name,tensor in state.items():
    if name.startswith("__cajita_q4_") or name in already_packed:
     continue
    if "scale" in name.rsplit(".",1)[-1].lower():
     continue
    if tensor.dtype not in (torch.float16,torch.bfloat16,torch.float32):
     continue
    original_tensor_bytes=tensor.numel()*tensor.element_size()
    if original_tensor_bytes < 262144 or tensor.numel() < 65536:
     continue
    eligible.append((name,tensor))
    dtype_key=str(tensor.dtype).replace("torch.","")
    dtype_bytes[dtype_key]=dtype_bytes.get(dtype_key,0)+original_tensor_bytes
   if not eligible:
    rows.append({"id":spec["id"],"path":spec["rel"],"original_bytes":original_bytes,
                 "original_sha256":original_hash,"status":"NO_LARGE_FLOAT_TENSORS_TO_PACK"})
    continue
   eligible_bytes=sum(t.numel()*t.element_size() for _,t in eligible)
   before_sidecar_bytes=sidecar.stat().st_size
   baseline=run_model_smoke(spec)
   row={"id":spec["id"],"path":spec["rel"],"original_bytes":original_bytes,
        "original_sidecar_bytes":before_sidecar_bytes,"original_sha256":original_hash,
        "eligible_tensor_count":len(eligible),"eligible_float_bytes":eligible_bytes,
        "eligible_dtypes_bytes":dtype_bytes,"attempts":[],"status":"NOT_PROMOTED"}
   row["baseline_smoke"]={"passed":baseline.get("passed",False),"status":baseline.get("status"),
                          "returncode":baseline.get("returncode"),"result":baseline.get("result",{})}
   if not baseline.get("passed"):
    row["status"]="BLOCKED_BASELINE_SMOKE_FAILED"
    rows.append(row); continue
   backup=tmp/"before.safetensors"; backup_meta=tmp/"before.q4.json"
   shutil.copy2(path,backup); shutil.copy2(sidecar,backup_meta)
   promoted=False
   for group_size in GROUP_SIZES:
    candidate=tmp/f"candidate_g{group_size}.safetensors"
    candidate_meta_path=tmp/f"candidate_g{group_size}.q4.json"
    candidate_state=dict(state); new_entries=[]
    for name,tensor in eligible:
     packed,scales,numel,shape=pack_float_tensor(tensor,group_size,torch)
     pkey="__cajita_q4_extra_packed__."+name
     skey="__cajita_q4_extra_scales__."+name
     candidate_state[pkey]=packed; candidate_state[skey]=scales
     del candidate_state[name]
     new_entries.append({"name":name,"packed_key":pkey,"scales_key":skey,
                         "shape":list(shape),"numel":numel,"group_size":group_size,
                         "original_dtype":str(tensor.dtype).replace("torch.",""),
                         "encoding":"SIGNED_INT4_BLOCKWISE"})
    try:
     save_file(candidate_state,str(candidate),metadata={"cajita_format":"CAJITA_Q4_BLOCK_PACKED/1.0"})
     candidate_hash=sha256(candidate)
     updated_meta=json.loads(json.dumps(current_meta))
     updated_meta["additional_tensors"]=updated_meta.get("additional_tensors",[])+new_entries
     updated_meta["deep_pack_pass"]={"group_size":group_size,"source_sha256":original_hash,
                                     "packed_tensor_count":len(new_entries),
                                     "packed_original_bytes":eligible_bytes}
     updated_meta["candidate_sha256"]=candidate_hash
     candidate_meta_path.write_text(json.dumps(updated_meta,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    except Exception as exc:
     row["attempts"].append({"group_size":group_size,"status":"CANDIDATE_BUILD_FAILED",
                             "error":type(exc).__name__+":"+str(exc)[:800]})
     continue
    candidate_total=candidate.stat().st_size+candidate_meta_path.stat().st_size
    original_total=original_bytes+before_sidecar_bytes
    if candidate_total>=original_total:
     row["attempts"].append({"group_size":group_size,"status":"CANDIDATE_WITH_SIDECAR_NOT_SMALLER",
                             "candidate_bytes":candidate.stat().st_size,
                             "candidate_sidecar_bytes":candidate_meta_path.stat().st_size})
     continue
    shutil.copy2(candidate,path); shutil.copy2(candidate_meta_path,sidecar)
    after=run_model_smoke(spec); same=signature_equal(spec,baseline,after)
    smoke_ok=bool(after.get("passed"))
    attempt={"group_size":group_size,"candidate_bytes":candidate.stat().st_size,
             "candidate_sidecar_bytes":candidate_meta_path.stat().st_size,
             "candidate_sha256":candidate_hash,"packed_tensor_count":len(new_entries),
             "packed_original_bytes":eligible_bytes,
             "runtime_smoke_after":{"passed":smoke_ok,"status":after.get("status"),
                 "returncode":after.get("returncode"),"result":after.get("result",{}),
                 "stderr_tail":after.get("stderr_tail","")},
             "smoke_signature_preserved":same,"smoke_passed":smoke_ok,
             "status":"PROMOTED" if smoke_ok else "ROLLBACK_RUNTIME_SMOKE_FAILURE"}
    row["attempts"].append(attempt)
    if smoke_ok:
     row.update({"status":"PROMOTED_FLOAT_Q4_BLOCKWISE","group_size":group_size,
                 "candidate_bytes":path.stat().st_size,"candidate_sidecar_bytes":sidecar.stat().st_size,
                 "candidate_sha256":sha256(path),
                 "saved_bytes":original_total-(path.stat().st_size+sidecar.stat().st_size),
                 "smoke_signature_preserved":same})
     promoted=True; break
    shutil.copy2(backup,path); shutil.copy2(backup_meta,sidecar)
   if not promoted:
    shutil.copy2(backup,path); shutil.copy2(backup_meta,sidecar)
    row["status"]="NO_FLOAT_Q4_CANDIDATE_PASSED_RUNTIME_SMOKE"
   rows.append(row)
 return rows

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
 q2_marker="## Segunda pasada de empaquetado de factores a 2 bits — 2026-10-23"
 if q2_marker not in text:
  q2_rows=[]
  for r in report.get("q2_factor_results",[]):
   q2_rows.append("| "+r["id"]+" | "+str(r.get("status","NOT_CHANGED"))+" | "+str(r.get("factor_tensor_count",0))+" | "+str(r.get("original_bytes",0))+" | "+str(r.get("candidate_bytes",r.get("original_bytes",0)))+" | "+str(r.get("saved_bytes",0))+" |")
  text += "\n\n"+q2_marker+"\n\nLos factores de bajo rango que ya estaban empaquetados en INT4 se recodificaron como enteros afines sin signo de 2 bits por bloque, con mínimos y pasos FP32 por grupo. Cada candidato se admite únicamente si reduce el total modelo+sidecar y la prueba de arranque/generación sigue pasando. La comparación de firma se registra, pero no equivale a equivalencia de calidad ni certificación.\n\n| Motor | Estado | Tensores factores | Bytes del modelo previos | Bytes candidatos/activos | Bytes netos ahorrados |\n|---|---|---:|---:|---:|---:|\n"+"\n".join(q2_rows)+"\n"
 deep_marker="## Segunda pasada de INT4 para tensores flotantes — 2026-10-23"
 if deep_marker not in text:
  rows=[]
  for r in report.get("float_tensor_results",[]):
   rows.append("| "+r["id"]+" | "+str(r.get("status","NOT_CHANGED"))+" | "+str(r.get("eligible_tensor_count",0))+" | "+str(r.get("eligible_float_bytes",0))+" | "+str(r.get("saved_bytes",0))+" |")
  text += "\n\n"+deep_marker+"\n\nSe empaquetaron tensores de precisión restantes en bloques INT4 con escala por bloque, manteniendo el mismo modelo lógico y restaurando el dtype original al cargar. Los candidatos se promueven solo si reducen el tamaño total (modelo más sidecar) y la prueba de arranque/generación sigue pasando. La firma de salida se registra separadamente; equivalencia de calidad y certificación no quedan establecidas.\n\n| Motor | Estado | Tensores empaquetados | Bytes originales elegibles | Bytes netos ahorrados |\n|---|---|---:|---:|---:|\n"+"\n".join(rows)+"\n"

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
 report["q2_factor_results"]=quantize_factor_models_q2(torch,load_file,save_file)
 report["float_tensor_results"]=quantize_remaining_float_tensors(torch,load_file,save_file)
 report["onnx_result"]=quantize_onnx()
 report["weights_manifest_sha256"]=update_manifest_and_doc()
 post,post_count=bytes_tree(RUNTIME)
 report["runtime_bytes_after"]=post; report["runtime_file_count_after"]=post_count
 report["saved_bytes"]=pre-post
 report["bytes_over_cap"]=max(0,post-HARD_CAP)
 report["size_gate"]="PASS" if post<=HARD_CAP else "FAIL"
 report["quantized_factor_models_promoted"]=sum(x.get("status")=="PROMOTED_Q4_BLOCKWISE" for x in report["weight_factor_results"])
 report["q2_factor_models_promoted"]=sum(x.get("status")=="PROMOTED_Q2_BLOCKWISE" for x in report.get("q2_factor_results",[]))
 report["q2_factor_bytes_saved"]=sum(int(x.get("saved_bytes",0)) for x in report.get("q2_factor_results",[]))
 report["float_tensor_models_promoted"]=sum(x.get("status")=="PROMOTED_FLOAT_Q4_BLOCKWISE" for x in report.get("float_tensor_results",[]))
 report["float_tensor_bytes_saved"]=sum(int(x.get("saved_bytes",0)) for x in report.get("float_tensor_results",[]))
 report["onnx_status"]=report["onnx_result"].get("status")
 report["quality_equivalence"]="SMOKE_SIGNATURE_ONLY; TASK_LEVEL_QUALITY_NOT_ESTABLISHED"
 report["independent_validation"]="NOT_RUN"
 report["certification"]="NOT_GRANTED"
 report["elapsed_seconds"]=round(time.monotonic()-started,3)
 report["status"]="SIZE_GATE_PASS_CERTIFICATION_NOT_GRANTED" if post<=HARD_CAP else "SIZE_GATE_FAIL_OPTIMIZATION_RESULTS_COMMITTED_FOR_NEXT_PASS"
 REPORT.parent.mkdir(parents=True,exist_ok=True)
 # Keep audit evidence byte-stable when the substantive outcome has not changed.
 # Otherwise this timestamp alone creates a bot commit on every no-op rebalance,
 # advances main during the factory/G23/G24 evidence chain, and causes source-SHA
 # races without promoting a single model. Wall-clock data remains in Actions logs.
 persist_report = True
 if REPORT.is_file() and not REPORT.is_symlink():
  try:
   previous = json.loads(REPORT.read_text(encoding="utf-8"))
   current_comparable = dict(report)
   previous_comparable = dict(previous) if isinstance(previous, dict) else {}
   for field in ("created_at_utc", "elapsed_seconds"):
    current_comparable.pop(field, None)
    previous_comparable.pop(field, None)
   if isinstance(previous, dict) and current_comparable == previous_comparable:
    persist_report = False
    print("REBALANCE_REPORT_UNCHANGED_NO_TIMESTAMP_ONLY_WRITE")
  except (OSError, UnicodeDecodeError, json.JSONDecodeError):
   # Invalid prior evidence is not treated as matching; write a fresh complete report.
   persist_report = True
 if persist_report:
  REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"status":report["status"],"runtime_bytes_before":pre,"runtime_bytes_after":post,
   "saved_bytes":pre-post,"hard_cap_bytes":HARD_CAP,"bytes_over_cap":report["bytes_over_cap"],
   "size_gate":report["size_gate"],"q4_models_promoted":report["quantized_factor_models_promoted"],
   "q2_factor_models_promoted":report["q2_factor_models_promoted"],"q2_factor_bytes_saved":report["q2_factor_bytes_saved"],
   "float_tensor_models_promoted":report["float_tensor_models_promoted"],"float_tensor_bytes_saved":report["float_tensor_bytes_saved"],
   "onnx_status":report["onnx_status"],"certification":report["certification"]},ensure_ascii=False))
 return 0

if __name__=="__main__": raise SystemExit(main())
