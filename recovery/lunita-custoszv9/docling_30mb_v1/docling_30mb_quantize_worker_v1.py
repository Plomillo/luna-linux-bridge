#!/usr/bin/env python3
"""CUSTOSZ V9 worker: extreme CPU-capable binary quantization for the existing Granite-Docling identity.

Text tensors use low-rank binary factors in the NanoQuant family; vision and connector
tensors use saliency/outlier-aware binary quantization in the Bi-VLM family. This is an
explicit CPU adaptation, not a claim that either upstream project ships an Idefics3 CPU
implementation. Originals remain read-only and no candidate is published unless the
30,000,000-byte gate and a real image-to-text startup smoke both pass.
"""
from __future__ import annotations
import argparse, atexit, datetime as dt, hashlib, importlib.util, json, os, pathlib, shutil, subprocess, sys, time, uuid
from safetensors import safe_open
import numpy as np
import torch
from huggingface_hub import snapshot_download

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
PRJ=HOME/"Proyectos/1. PROYECTOS PRIORITARIOS/1. PROYECTO LUNA/2. Cajita de Luna"
DOC=PRJ/"5. Inteligencia documental"
ROOT=HOME/"Proyectos/1. PROYECTOS PRIORITARIOS/5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
RT=ROOT/"CUSTOSZ_CONTINUITY_V1"
STATE=RT/"state"
JOB=STATE/"jobs/docling_30mb_lane_v1"
WORKER_STATE=STATE/"jobs/docling_30mb_worker_v1"
CANDIDATES=STATE/"cajita_candidates"
HF_REPO="ibm-granite/granite-docling-258M"
HF_REVISION="982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe"
CAP=30_000_000
SOURCES={
 "granite_docling_q4_gguf":{"path":DOC/"Docling/granite-docling-258M-Q4_K_M.gguf","sha256":"4ba41a480d2b6594613a23819df8fcc382d9dab9691e28bf327b3ac799fe0a82","bytes":138559520},
 "granite_docling_mmproj_f16":{"path":DOC/"Docling/mmproj-granite-docling-258M-f16.gguf","sha256":"4b7b2c4ed3162bd9cb323668c188e2324838b8f8ca4f3f9767f16c4c600d43ad","bytes":190031712},
 "docling_slim_wheel":{"path":DOC/"Docling/docling_slim-2.124.0-py3-none-any.whl","sha256":"2c7c667394d3eae9080bc15143ed6f1d39a4838090d9e3f29be212606e6676bd","bytes":780430},
 "calibre_binary_reference":{"path":DOC/"Calibre/calibre-9.14.0-x86_64.txz","sha256":"7f53a0863ed6d32407bc72053b966e39d5b64813f2592bd9c741504c01c0e7f3","bytes":192898432},
 "calibre_source_reference":{"path":DOC/"Calibre/calibre-9.14.0.tar.xz","sha256":"d1bc24024b0942429c627e9c5d0b25d51df9c1af1e1d8dca3e572f03b194c561","bytes":48867616},
}
RUNTIME_SRC=JOB/"docling_30mb_runtime_v1.py"
V9_PATH=ROOT/"CUSTOSZV9.pyz"
MISSION_ID="CUSTOSZV9_DOCLING_INTELIGENCIA_DOCUMENTAL_30MB_BIVLM_NQ_V1"
SEED=20261021
# Target per-layer settings are fixed and recorded before execution. The hard byte gate
# is measured after all model, tokenizer, processor, config and runtime-shim files exist.
TEXT_RANK_FRACTION=0.20
EMBED_RANK_FRACTION=0.16
VISION_OUTLIER_FRACTION=0.00005  # 0.005% residual entries retained in FP16.
ASSETS=("LICENSE","config.json","generation_config.json","preprocessor_config.json","processor_config.json",
        "tokenizer.json","tokenizer_config.json","special_tokens_map.json","added_tokens.json",
        "chat_template.json","chat_template.jinja")

def utc():
 return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def sha_file(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
 return h.hexdigest()
def canon(x):
 return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def atomic(path,obj,exclusive=False):
 path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 if exclusive and path.exists(): raise RuntimeError("APPEND_ONLY_COLLISION:"+str(path))
 tmp=path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
 with tmp.open("x",encoding="utf-8") as f:
  json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
 os.chmod(tmp,0o600); os.replace(tmp,path)
def event(state_dir,event_type,payload):
 state_dir=pathlib.Path(state_dir); state_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
 p=state_dir/"events.jsonl"; seq=1; prev="0"*64
 if p.exists():
  with p.open("r",encoding="utf-8") as f:
   for line in f:
    row=json.loads(line); seq=row["sequence"]+1; prev=row["event_sha256"]
 row={"sequence":seq,"timestamp_utc":utc(),"mission_id":MISSION_ID,"event_type":event_type,
      "payload":payload,"previous_event_sha256":prev}
 row["event_sha256"]=hashlib.sha256(canon(row)).hexdigest()
 fd=os.open(str(p),os.O_CREAT|os.O_WRONLY|os.O_APPEND,0o600)
 try: os.write(fd,(json.dumps(row,sort_keys=True,ensure_ascii=False)+"\n").encode()); os.fsync(fd)
 finally: os.close(fd)
 print(json.dumps({"event":event_type,"sequence":seq,"payload":payload},ensure_ascii=False),flush=True)
 return row
def tree_bytes(root):
 return sum(p.stat().st_size for p in pathlib.Path(root).rglob("*") if p.is_file())
def preflight_sources():
 found={}
 for name,s in SOURCES.items():
  p=pathlib.Path(s["path"])
  if not p.is_file(): raise RuntimeError("PINNED_SOURCE_MISSING:"+name)
  size=p.stat().st_size; digest=sha_file(p)
  if size!=s["bytes"] or digest!=s["sha256"]: raise RuntimeError("PINNED_SOURCE_MISMATCH:"+name)
  found[name]={"path":str(p),"bytes":size,"sha256":digest,"read_only":True}
 return found
def packbits(sign_array):
 return np.packbits(np.asarray(sign_array,dtype=np.uint8).reshape(-1),bitorder="little").tobytes()
def append_bytes(out,data):
 offset=out.tell(); out.write(data); return offset,len(data)
def f16_bytes(x):
 return np.asarray(x,dtype="<f2").tobytes(order="C")
def randomized_binary_lowrank(w,key,rank,seed):
 # Randomized range finder + truncated SVD initializes the low-rank binary factors.
 # Factor entries are row-scaled signs, an inference-friendly sub-1-bit representation.
 a=torch.as_tensor(np.asarray(w,dtype=np.float32),dtype=torch.float32,device="cpu").contiguous()
 m,n=a.shape; rank=max(1,min(int(rank),m,n)); oversample=min(8,max(2,min(m,n)-rank)); k=min(min(m,n),rank+oversample)
 gen=torch.Generator(device="cpu"); gen.manual_seed(seed)
 omega=torch.randn((n,k),generator=gen,dtype=torch.float32)
 y=a@omega
 q,_=torch.linalg.qr(y,mode="reduced")
 if a.numel()<=8_000_000 and rank<=160:
  z=a.T@q; q,_=torch.linalg.qr(a@z,mode="reduced")
 small=q.T@a
 ub,s,vh=torch.linalg.svd(small,full_matrices=False)
 u=q@ub[:,:rank]; s=s[:rank]; vh=vh[:rank,:]
 root=torch.sqrt(torch.clamp(s,min=0)).unsqueeze(0)
 A=u*root; B=root.T*vh
 sa=A.abs().mean(dim=1).clamp_min(1e-8); sb=B.abs().mean(dim=1).clamp_min(1e-8)
 sa=sa.numpy().astype("<f2"); sb=sb.numpy().astype("<f2")
 asgn=(A.numpy()>=0); bsgn=(B.numpy()>=0)
 return (m,n,rank,packbits(asgn),f16_bytes(sa),packbits(bsgn),f16_bytes(sb))
def binary_with_outliers(w,key,frac):
 a=np.asarray(w,dtype=np.float32)
 orig_shape=tuple(a.shape)
 if a.ndim==4:
  mat=a.reshape(a.shape[0],-1)
 elif a.ndim==3 and a.shape[0]==1:
  mat=a.reshape(a.shape[1],a.shape[2])
 elif a.ndim>=2:
  mat=a.reshape(a.shape[0],-1)
 else:
  mat=a.reshape(1,-1)
 rows,cols=mat.shape
 scales=np.mean(np.abs(mat),axis=1,dtype=np.float64).astype(np.float32)
 signs=(mat>=0)
 approx=np.where(signs,scales[:,None],-scales[:,None])
 resid=mat-approx
 k=min(mat.size,max(0,int(mat.size*frac)))
 if k:
  flat=np.abs(resid).reshape(-1)
  ids=np.argpartition(flat,-k)[-k:].astype("<u4")
  vals=resid.reshape(-1)[ids.astype(np.int64)].astype("<f2")
  order=np.argsort(ids,kind="stable"); ids=ids[order]; vals=vals[order]
 else:
  ids=np.empty((0,),dtype="<u4"); vals=np.empty((0,),dtype="<f2")
 return orig_shape,(rows,cols),packbits(signs),f16_bytes(scales),ids.tobytes(),vals.tobytes(),int(k)
def write_record(out,key,tensor,cfg,tie):
 # A tied output projection is an alias, not duplicate payload.
 if key=="lm_head.weight" and tie:
  return {"name":key,"kind":"alias","target":"model.text_model.embed_tokens.weight","shape":list(tensor.shape)}
 is_text=(key.startswith("model.text_model.") or key.startswith("lm_head."))
 arr=tensor.detach().to("cpu").float().numpy()
 shape=tuple(arr.shape)
 is_weight=key.endswith(".weight") or key=="lm_head.weight"
 if is_text and is_weight and arr.ndim>=2:
  if key.endswith("embed_tokens.weight") or key=="lm_head.weight":
   m,n=arr.shape[-2:] if arr.ndim>2 else arr.shape
   r=max(32,int(min(m,n)*EMBED_RANK_FRACTION))
  else:
   # Patch/position tables with more than two dimensions are kept on the robust
   # vision-style encoder unless they belong to the language token embedding.
   if arr.ndim!=2:
    is_text=False
   else:
    m,n=arr.shape; r=max(8,int(min(m,n)*TEXT_RANK_FRACTION))
  if is_text and arr.ndim>=2:
   if arr.ndim>2: mat=arr.reshape(arr.shape[0],-1); shape=tuple(arr.shape)
   else: mat=arr
   m,n,rank,ab,asb,bb,bsb=randomized_binary_lowrank(mat,key,r,
          int(hashlib.sha256((key+str(SEED)).encode()).hexdigest()[:8],16))
   rec={"name":key,"kind":"nanoquant_style_binary_lowrank","shape":list(shape),"matrix_shape":[m,n],"rank":rank}
   rec["a_sign_offset"],rec["a_sign_nbytes"]=append_bytes(out,ab)
   rec["a_scale_offset"],rec["a_scale_nbytes"]=append_bytes(out,asb)
   rec["b_sign_offset"],rec["b_sign_nbytes"]=append_bytes(out,bb)
   rec["b_scale_offset"],rec["b_scale_nbytes"]=append_bytes(out,bsb)
   return rec
 if not is_text and is_weight and arr.ndim>=2:
  orig_shape,mat_shape,sign,scales,idx,vals,k=binary_with_outliers(arr,key,VISION_OUTLIER_FRACTION)
  rec={"name":key,"kind":"bivlm_binary_outliers","shape":list(orig_shape),"matrix_shape":list(mat_shape),
       "outlier_count":k,"outlier_fraction":VISION_OUTLIER_FRACTION}
  rec["sign_offset"],rec["sign_nbytes"]=append_bytes(out,sign)
  rec["scale_offset"],rec["scale_nbytes"]=append_bytes(out,scales)
  rec["outlier_index_offset"],_=append_bytes(out,idx)
  rec["outlier_value_offset"],_=append_bytes(out,vals)
  return rec
 # Biases, norms and small non-matrix metadata are retained losslessly to FP16.
 arr16=arr.astype("<f2"); data=arr16.tobytes(order="C")
 off,nbytes=append_bytes(out,data)
 return {"name":key,"kind":"fp16","shape":list(shape),"offset":off,"nbytes":nbytes}
def ensure_pillow(vendor_dir):
 try:
  import PIL
  return {"available":True,"version":getattr(PIL,"__version__","unknown"),"vendor_path":None}
 except Exception: pass
 vendor_dir=pathlib.Path(vendor_dir); vendor_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
 # Install only into task-scoped vendor storage; never mutate the pinned CUSTOSZ toolchain.
 cmd=[sys.executable,"-m","pip","install","--disable-pip-version-check","--no-warn-script-location",
      "--no-cache-dir","--target",str(vendor_dir),"Pillow==11.3.0"]
 proc=subprocess.run(cmd,capture_output=True,text=True,timeout=300,check=False)
 if proc.returncode: raise RuntimeError("PILLOW_SCOPED_INSTALL_FAILED:"+proc.stderr[-1200:])
 sys.path.insert(0,str(vendor_dir))
 import PIL
 return {"available":True,"version":getattr(PIL,"__version__","unknown"),"vendor_path":str(vendor_dir),
         "pip_stdout_tail":proc.stdout[-600:]}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--run",action="store_true"); ap.add_argument("--job-dir",default=str(WORKER_STATE))
 a=ap.parse_args()
 if not a.run: ap.error("explicit --run required")
 jdir=pathlib.Path(a.job_dir).resolve(); jdir.mkdir(parents=True,exist_ok=True,mode=0o700)
 lock=jdir/"worker.lock"
 try: fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 except FileExistsError:
  try:
   old_pid=int(lock.read_text().strip()); os.kill(old_pid,0)
  except (ValueError,ProcessLookupError,FileNotFoundError,PermissionError):
   stale=lock.with_name("worker.lock.stale."+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
   os.replace(lock,stale); fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
  else: raise RuntimeError("DOCLING_WORKER_SINGLETON_LOCK_EXISTS:"+str(old_pid))
 os.write(fd,str(os.getpid()).encode()); os.fsync(fd); os.close(fd)
 def release_lock():
  try:
   if int(lock.read_text().strip())==os.getpid(): lock.unlink()
  except Exception: pass
 atexit.register(release_lock)
 started=utc(); stage=jdir/("staging_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")+"_"+uuid.uuid4().hex[:8])
 stage.mkdir(parents=True,exist_ok=False,mode=0o700); cand_id="GRANITE_DOCLING_258M_BIVLM_NQ_CPU_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
 receipt={"schema":"DOCLING_30MB_WORKER_RESULT/1.0","mission_id":MISSION_ID,"candidate_id":cand_id,
  "started_at_utc":started,"finished_at_utc":None,"phase":"PREFLIGHT","status":"RUNNING",
  "hard_cap_bytes":CAP,"source_files_modified":False,"canonical_promotion":"NOT_AUTHORIZED",
  "startup_certification":"NOT_GRANTED","quality_equivalence":"NOT_ESTABLISHED"}
 atomic(jdir/"progress.json",receipt)
 try:
  src=preflight_sources()
  event(jdir,"SOURCE_HASHES_VERIFIED",{"sources":src,"source_mutation":False})
  hfcache=STATE/"cache/huggingface_granite_docling_258m"
  snapshot=pathlib.Path(snapshot_download(repo_id=HF_REPO,revision=HF_REVISION,cache_dir=str(hfcache),
      allow_patterns=["config.json","generation_config.json","preprocessor_config.json","processor_config.json",
       "tokenizer.json","tokenizer_config.json","special_tokens_map.json","added_tokens.json",
       "chat_template.json","chat_template.jinja","LICENSE","*.safetensors","*.safetensors.index.json"]))
  cfg=json.loads((snapshot/"config.json").read_text(encoding="utf-8"))
  if cfg.get("model_type")!="idefics3" or "Idefics3ForConditionalGeneration" not in cfg.get("architectures",[]):
   raise RuntimeError("PINNED_HF_MODEL_IDENTITY_MISMATCH")
  source_weights=sorted(snapshot.glob("*.safetensors"))
  if not source_weights: raise RuntimeError("OFFICIAL_SAFETENSORS_WEIGHTS_ABSENT")
  weight_hashes={p.name:{"bytes":p.stat().st_size,"sha256":sha_file(p)} for p in source_weights}
  event(jdir,"PINNED_MODEL_REVISION_READY",{"repo":HF_REPO,"revision":HF_REVISION,"config_sha256":sha_file(snapshot/"config.json"),
       "weights":weight_hashes,"architecture":cfg.get("architectures"),"local_candidate_hashes":src})
  (stage/"config.json").write_bytes((snapshot/"config.json").read_bytes())
  for name in ASSETS:
   p=snapshot/name
   if p.is_file(): shutil.copy2(p,stage/name)
  shutil.copy2(RUNTIME_SRC,stage/"docling_30mb_runtime_v1.py")
  if not (stage/"tokenizer.json").is_file(): raise RuntimeError("TOKENIZER_JSON_REQUIRED_FOR_OFFLINE_STARTUP")
  tie=bool(cfg.get("text_config",{}).get("tie_word_embeddings",cfg.get("tie_word_embeddings",False)))
  allkeys=[]
  for p in source_weights:
   with safe_open(str(p),framework="pt",device="cpu") as sf:
    for k in sf.keys(): allkeys.append((p,k))
  records={}; total=len(allkeys)
  receipt.update({"phase":"QUANTIZING","source_tensor_count":total,"hf_snapshot":str(snapshot),"hf_revision":HF_REVISION})
  atomic(jdir/"progress.json",receipt)
  event(jdir,"QUANTIZATION_START",{"tensor_count":total,"method":{
      "text":"randomized-SVD initialized row-scaled binary low-rank factors, NanoQuant-family adaptation",
      "vision_connector":"row-scaled binary weights plus sparse FP16 residual outliers, Bi-VLM-family adaptation",
      "device":"CPU; no CUDA device exists on LOUKSNA","source":"same pinned Granite-Docling model ID; local Q4 GGUF and mmproj are preserved read-only"}})
  blob_path=stage/"quantized_weights.bin"
  t0=time.time()
  with blob_path.open("xb") as out:
   for i,(f,key) in enumerate(allkeys,1):
    with safe_open(str(f),framework="pt",device="cpu") as sf: tensor=sf.get_tensor(key)
    rec=write_record(out,key,tensor,cfg,tie); records[key]=rec
    if i==1 or i%20==0 or i==total:
     out.flush(); os.fsync(out.fileno())
     receipt.update({"phase":"QUANTIZING","tensors_done":i,"source_tensor_count":total,
       "model_weight_bytes_written":out.tell(),"elapsed_seconds":round(time.time()-t0,2)})
     atomic(jdir/"progress.json",receipt)
     event(jdir,"QUANTIZATION_PROGRESS",{"done":i,"total":total,"bytes_written":out.tell(),"last_tensor":key})
    del tensor
  # Deterministically keep only operational model/tokenizer files; model source weights
  # are never copied into the candidate bundle.
  manifest={"schema":"DOCLING_BINARY_QUANTIZED_MANIFEST/1.0","candidate_id":cand_id,
   "created_at_utc":utc(),"hard_cap_bytes":CAP,"model_id":HF_REPO,"model_revision":HF_REVISION,
   "architecture":cfg["architectures"][0],"tie_word_embeddings":tie,
   "hard_cap_scope":"DOCILING_GRANITE_DOCLING_MODEL_BUNDLE_ONLY; Calibre and docling_slim remain separate registered resources, not silently removed or represented as included",
   "source_local_artifacts":src,"source_hf_config_sha256":sha_file(snapshot/"config.json"),
   "source_hf_weight_hashes":weight_hashes,"method":{
    "text":"NanoQuant-family low-rank binary factorization; randomized-SVD initialization, row scales, CPU-compatible decode",
    "vision_connector":"Bi-VLM-family hybrid binary sign quantization with retained residual outliers",
    "upstream_implementation_note":"CPU/Idefics3 adaptation; not an unmodified upstream NanoQuant or Bi-VLM executable"},
   "settings":{"text_rank_fraction":TEXT_RANK_FRACTION,"embedding_rank_fraction":EMBED_RANK_FRACTION,
    "vision_outlier_fraction":VISION_OUTLIER_FRACTION,"seed":SEED},
   "external_runtime_dependencies":{"python":"3.13","torch":"2.11.0+cpu","transformers":"4.57.6",
      "safetensors":"0.8.0","numpy":"2.2.6","Pillow":"11.3.0 task-scoped for smoke"},
   "tensors":records,"weights_sha256":sha_file(blob_path)}
  atomic(stage/"quantized_manifest.json",manifest,exclusive=True)
  bundle_bytes=tree_bytes(stage)
  receipt.update({"phase":"SIZE_GATE","candidate_id":cand_id,"candidate_staging_path":str(stage),
       "candidate_bundle_bytes":bundle_bytes,"quantized_weights_bytes":blob_path.stat().st_size,
       "hard_cap_bytes":CAP,"size_gate":"PASS" if bundle_bytes<=CAP else "FAIL",
       "weights_sha256":manifest["weights_sha256"]})
  atomic(jdir/"progress.json",receipt)
  event(jdir,"SIZE_GATE_EVALUATED",{"candidate_bundle_bytes":bundle_bytes,"hard_cap_bytes":CAP,
       "status":"PASS" if bundle_bytes<=CAP else "FAIL","bundle_includes":["quantized_weights.bin","manifest","config","tokenizer","processor assets","runtime shim"]})
  if bundle_bytes>CAP: raise RuntimeError("HARD_BYTE_GATE_EXCEEDED:"+str(bundle_bytes))
  vendor=jdir/"vendor_pillow"; pillow=ensure_pillow(vendor)
  runtime_mod_path=stage/"docling_30mb_runtime_v1.py"
  spec=importlib.util.spec_from_file_location("docling_30mb_runtime_v1",runtime_mod_path)
  runtime=importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)
  smoke=runtime.smoke(str(stage),max_new_tokens=48)
  atomic(jdir/"runtime_smoke.json",smoke,exclusive=True)
  event(jdir,"RUNTIME_STARTUP_SMOKE_PASS",smoke)
  # Write startup evidence into staging first; publish only after the final gross size check.
  final=CANDIDATES/cand_id
  if final.exists(): raise RuntimeError("CANDIDATE_ID_COLLISION")
  fm=json.loads((stage/"quantized_manifest.json").read_text(encoding="utf-8"))
  fm["published_candidate_path"]=str(final)
  fm["runtime_startup_smoke"]={"status":"PASS","receipt_path":str(jdir/"runtime_smoke.json")}
  atomic(stage/"quantized_manifest.json",fm)
  staged_final_bytes=tree_bytes(stage)
  if staged_final_bytes>CAP: raise RuntimeError("FINAL_STAGING_SIZE_GATE_FAILURE:"+str(staged_final_bytes))
  final.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  os.replace(stage,final)
  final_bytes=tree_bytes(final)
  if final_bytes>CAP: raise RuntimeError("POST_RENAME_SIZE_GATE_FAILURE")
  receipt.update({"phase":"STARTUP_VERIFIED","status":"STARTUP_PASS","finished_at_utc":utc(),
   "published_candidate_path":str(final),"candidate_bundle_bytes":final_bytes,"hard_cap_bytes":CAP,
   "size_gate":"PASS","runtime_smoke":"PASS","runtime_smoke_receipt":str(jdir/"runtime_smoke.json"),
   "pillow":pillow,"startup_certification":"PASS","model_quality_certification":"NOT_GRANTED",
   "quality_equivalence":"NOT_ESTABLISHED","canonical_promotion":"NOT_AUTHORIZED","source_files_modified":False})
  atomic(jdir/"progress.json",receipt)
  output=STATE/"worker_outputs"/("DOCLING_30MB_STARTUP_CERT_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".json")
  atomic(output,receipt,exclusive=True)
  event(jdir,"STARTUP_GATE_CERTIFIED",{"candidate_path":str(final),"bytes":final_bytes,"cap":CAP,
       "runtime_smoke":"PASS","quality_equivalence":"NOT_ESTABLISHED","canonical_promotion":"NOT_AUTHORIZED"})
  print(json.dumps(receipt,indent=2,ensure_ascii=False),flush=True)
  return 0
 except Exception as e:
  receipt.update({"phase":"FAILED_OR_HELD","status":"HOLD","finished_at_utc":utc(),
    "error":type(e).__name__+":"+str(e),"candidate_staging_path":str(stage),
    "startup_certification":"NOT_GRANTED","model_quality_certification":"NOT_GRANTED",
    "canonical_promotion":"NOT_AUTHORIZED","source_files_modified":False})
  atomic(jdir/"progress.json",receipt)
  try: event(jdir,"QUANTIZATION_OR_STARTUP_HOLD",{"error":receipt["error"],"staging_path":str(stage)})
  except Exception: pass
  print(json.dumps(receipt,indent=2,ensure_ascii=False),file=sys.stderr,flush=True)
  raise
if __name__=="__main__": raise SystemExit(main())
