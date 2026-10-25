#!/usr/bin/env python3
"""Fail-closed task adapters for the materialized Cajita six-domain candidate."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, platform, re, resource, subprocess, sys, time
from pathlib import Path
from cajita_tokenizer_materializer import MANIFEST_NAME as TOKENIZER_MANIFEST_NAME, TokenizerMaterializationError, tokenizer_tree_rows

REQUEST_SCHEMA = "CAJITA_TASK_REQUEST/1.0"
RESULT_SCHEMA = "CAJITA_TASK_RESULT/1.0"
MANIFEST_SHA = "703fb6b4c278b6111a354951bb7f9faf3721edb0c89b4dda843242e47634039d"
CANDIDATE_ID = "CAJITA_LUNA_RUNTIME_V9_20261023"
MAX_TEXT, MAX_AUDIO, MAX_IMAGE, MAX_TOKENS, MAX_TIMEOUT = 16384, 32*1024*1024, 24*1024*1024, 128, 1800

ADAPTERS = {
 "D01_CEREBRO": {"weight":"1. Cerebro/model.safetensors","sha":"e2516453d09285581bd6f3bf45a4c3a9fa6431bdc3dff56e7249d30e4e294ae0","bytes":40489120,"module":"1. Cerebro","target":"D01_CEREBRO_ROOT","entry":"1. Cerebro/cerebro_180mb_runtime.py","op":"generate_text","id":"CAJITA_CEREBRO_TEXT_GENERATION/1.0","tokens":8},
 "D03_TRANSCRIPCION": {"weight":"3. Transcripción/model.safetensors","sha":"67ee70beb2fb3529270a8169fbb6bd0f538912a064a6a303bec238647b4a5f5f","bytes":10399882,"module":"3. Transcripción","target":"D03_TRANSCRIPCION_ROOT","entry":"3. Transcripción/lowrank_runtime.py","op":"transcribe_audio","id":"CAJITA_WHISPER_TRANSCRIPTION/1.0","tokens":8},
 "D04_TRADUCTOR_INTELIGENTE": {"weight":"4. Traductor Inteligente/Traducción general/model.safetensors","sha":"630aad9958f9c78603852c29c382b0fe9d63e64772e21dc6367875a91dc6a28f","bytes":11720882,"module":"4. Traductor Inteligente/Traducción general","target":"D04_TRADUCCION_GENERAL","entry":"4. Traductor Inteligente/Traducción general/lowrank_runtime.py","op":"translate_text","id":"CAJITA_SEAMLESS_TRANSLATION/1.0","tokens":8},
 "D05_INTELIGENCIA_DOCUMENTAL": {"weight":"5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_weights.bin","sha":"4a13b916b63b682a28c8fe89fc608b90d3bf5a8a77cb0988e1e19131c64ebc88","bytes":13483380,"module":"5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate","target":"D05_DOCLING","entry":"5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/docling_30mb_runtime_v1.py","op":"extract_document_image","id":"CAJITA_DOCLING_IMAGE_EXTRACTION/1.0","tokens":24},
 "D06_SISTEMA_INTELIGENTE": {"weight":"6. Sistema Inteligente/Análisis Avanzado/model.safetensors","sha":"01eba827b9dd001a2352f0fd28a0bea229d3a5b3a78a41f3ea3e7c6c21995f56","bytes":14956240,"module":"6. Sistema Inteligente/Análisis Avanzado","target":"D06_ANALISIS_AVANZADO","entry":"6. Sistema Inteligente/Análisis Avanzado/lowrank_runtime_v2.py","op":"analyze_reasoning","id":"CAJITA_QWEN3_REASONING/1.0","tokens":8},
}
PLAN_ONLY={"domain":"D02_ORQUESTACION","op":"route_plan","id":"CAJITA_CANONICAL_ROUTE_PLANNER/PLAN_ONLY"}
LANGS={"en":"eng","eng":"eng","es":"spa","spa":"spa","fr":"fra","fra":"fra","de":"deu","deu":"deu","pt":"por","por":"por","it":"ita","ita":"ita","zh":"cmn","cmn":"cmn","ja":"jpn","jpn":"jpn","ko":"kor","kor":"kor","ru":"rus","rus":"rus","ar":"arb","arb":"arb"}

class AdapterError(RuntimeError): pass
def utc_now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def digest_bytes(data): return hashlib.sha256(data).hexdigest()
def digest_file(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
 return h.hexdigest()
def reject_symlinks(path):
 for p in (path,*path.parents):
  if p.is_symlink(): raise AdapterError("SYMLINK_PATH_REJECTED")
def input_file(value,root,field,cap,suffixes):
 if not isinstance(value,str) or not value.strip(): raise AdapterError("INPUT_FILE_PATH_REQUIRED:"+field)
 p=Path(value).expanduser()
 if not p.is_absolute(): p=root/p
 p=Path(os.path.abspath(str(p)));reject_symlinks(p)
 try:p=p.resolve(strict=True)
 except OSError as e: raise AdapterError("INPUT_FILE_NOT_FOUND:"+field) from e
 if not p.is_file() or p.suffix.lower() not in suffixes: raise AdapterError("INPUT_FILE_FORMAT_NOT_SUPPORTED:"+field)
 if not 0<p.stat().st_size<=cap: raise AdapterError("INPUT_FILE_SIZE_OUT_OF_RANGE:"+field)
 return p
def required_text(value,field):
 if not isinstance(value,str) or not value.strip(): raise AdapterError("INPUT_TEXT_REQUIRED:"+field)
 if len(value)>MAX_TEXT: raise AdapterError("INPUT_TEXT_TOO_LONG:"+field)
 return value
def normalize(record,root,timeout_cap=600):
 if not isinstance(record,dict) or record.get("schema")!=REQUEST_SCHEMA: raise AdapterError("REQUEST_SCHEMA_MISMATCH")
 tid=record.get("task_id")
 if not isinstance(tid,str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}",tid) is None: raise AdapterError("TASK_ID_INVALID")
 domain,op,payload=record.get("domain_id"),record.get("operation"),record.get("input")
 limits=record.get("limits",{})
 if not isinstance(payload,dict) or not isinstance(limits,dict): raise AdapterError("REQUEST_INPUT_OR_LIMITS_INVALID")
 if isinstance(timeout_cap,bool) or not isinstance(timeout_cap,int) or not 1<=timeout_cap<=MAX_TIMEOUT: raise AdapterError("CALLER_TIMEOUT_CAP_INVALID")
 timeout=limits.get("timeout_seconds",min(600,timeout_cap))
 if isinstance(timeout,bool) or not isinstance(timeout,int) or not 1<=timeout<=min(MAX_TIMEOUT,timeout_cap): raise AdapterError("TIMEOUT_LIMIT_INVALID")
 if domain==PLAN_ONLY["domain"]:
  if op!=PLAN_ONLY["op"]: raise AdapterError("DOMAIN_OPERATION_NOT_REGISTERED")
  text=required_text(payload.get("request_text"),"request_text")
  command=payload.get("route_command")
  if command is not None and not isinstance(command,str): raise AdapterError("ROUTE_COMMAND_INVALID")
  return {"task_id":tid,"domain_id":domain,"operation":op,"adapter_id":PLAN_ONLY["id"],"input":{"request_text":text,"route_command":command},"limits":{"timeout_seconds":timeout},"input_files":[]}
 spec=ADAPTERS.get(domain)
 if not spec: raise AdapterError("DOMAIN_TASK_ADAPTER_NOT_REGISTERED")
 if op!=spec["op"]: raise AdapterError("DOMAIN_OPERATION_NOT_REGISTERED")
 data={}; files=[]
 if domain=="D01_CEREBRO": data["prompt"]=required_text(payload.get("prompt"),"prompt")
 elif domain=="D03_TRANSCRIPCION":
  p=input_file(payload.get("audio_path"),root,"audio_path",MAX_AUDIO,{".wav"});data["audio_path"]=str(p);files.append({"field":"audio_path","bytes":p.stat().st_size,"sha256":digest_file(p)})
 elif domain=="D04_TRADUCTOR_INTELIGENTE":
  data["text"]=required_text(payload.get("text"),"text")
  for field in ("src_lang","tgt_lang"):
   raw=payload.get(field);lang=LANGS.get(raw.strip().lower()) if isinstance(raw,str) else None
   if not lang: raise AdapterError("LANGUAGE_CODE_NOT_REGISTERED:"+field)
   data[field]=lang
  if data["src_lang"]==data["tgt_lang"]: raise AdapterError("SOURCE_AND_TARGET_LANGUAGE_IDENTICAL")
 elif domain=="D05_INTELIGENCIA_DOCUMENTAL":
  p=input_file(payload.get("image_path"),root,"image_path",MAX_IMAGE,{".png",".jpg",".jpeg",".webp",".bmp"})
  data["image_path"]=str(p);data["prompt"]=required_text(payload.get("prompt","Extract visible text and fields."),"prompt")
  files.append({"field":"image_path","bytes":p.stat().st_size,"sha256":digest_file(p)})
 else:data["prompt"]=required_text(payload.get("prompt"),"prompt")
 tokens=limits.get("max_new_tokens",spec["tokens"])
 if isinstance(tokens,bool) or not isinstance(tokens,int) or not 1<=tokens<=MAX_TOKENS: raise AdapterError("MAX_NEW_TOKENS_OUT_OF_RANGE")
 return {"task_id":tid,"domain_id":domain,"target_id":spec["target"],"operation":op,"adapter_id":spec["id"],"input":data,"limits":{"timeout_seconds":timeout,"max_new_tokens":tokens},"input_files":files}
def tree_rows(directory):
 rows=[]
 for base,dirs,files in os.walk(directory,topdown=True,followlinks=False):
  bp=Path(base)
  if any((bp/d).is_symlink() for d in dirs): raise AdapterError("MODULE_SYMLINK_DIRECTORY_REJECTED")
  dirs[:]=sorted(dirs)
  for name in sorted(files):
   p=bp/name
   if name=="CAJITA_MODULE.json":continue
   if p.is_symlink() or not p.is_file():raise AdapterError("MODULE_NON_REGULAR_FILE_REJECTED")
   rows.append({"path":p.relative_to(directory).as_posix(),"bytes":p.stat().st_size,"sha256":digest_file(p)})
 return sorted(rows,key=lambda x:x["path"].encode("utf-8"))
def verify_integrity(root,domain):
 spec=ADAPTERS[domain];root=root.resolve()
 manifest=root/"CAJITA_RUNTIME_V1"/"weights_manifest.json"
 if manifest.is_symlink() or not manifest.is_file() or digest_file(manifest)!=MANIFEST_SHA:raise AdapterError("WEIGHT_MANIFEST_MISSING_OR_HASH_MISMATCH")
 data=json.loads(manifest.read_text(encoding="utf-8"))
 if data.get("schema")!="CAJITA_SIX_DOMAIN_WEIGHT_MANIFEST/1.0" or data.get("candidate_id")!=CANDIDATE_ID:raise AdapterError("WEIGHT_MANIFEST_IDENTITY_MISMATCH")
 matches=[x for x in data.get("artifacts",[]) if x.get("path")==spec["weight"]]
 if len(matches)!=1 or matches[0].get("sha256")!=spec["sha"] or int(matches[0].get("bytes",-1))!=spec["bytes"]:raise AdapterError("WEIGHT_MANIFEST_ENTRY_MISMATCH")
 weight=root/spec["weight"]
 if weight.is_symlink() or not weight.is_file() or weight.stat().st_size!=spec["bytes"] or digest_file(weight)!=spec["sha"]:raise AdapterError("MODEL_WEIGHT_IDENTITY_MISMATCH")
 module=root/spec["module"]; descriptor=module/"CAJITA_MODULE.json"
 if module.is_symlink() or not module.is_dir() or descriptor.is_symlink() or not descriptor.is_file():raise AdapterError("TARGET_MODULE_DESCRIPTOR_MISSING")
 meta=json.loads(descriptor.read_text(encoding="utf-8"))
 if meta.get("target_id")!=spec["target"]:raise AdapterError("TARGET_MODULE_IDENTITY_MISMATCH")
 rows=tree_rows(module)
 tokenizer_manifest=root/TOKENIZER_MANIFEST_NAME
 if tokenizer_manifest.is_file():
  try: rows=tokenizer_tree_rows(module,root,rows)
  except TokenizerMaterializationError as exc: raise AdapterError("TOKENIZER_TREE_INTEGRITY_INVALID:"+str(exc)[:180]) from exc
 integ=meta.get("tree_integrity",{})
 treehash=digest_bytes(json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8"))
 if len(rows)!=int(integ.get("file_count_excluding_module_descriptors",-1)):raise AdapterError("TARGET_MODULE_FILE_COUNT_MISMATCH")
 if sum(x["bytes"] for x in rows)!=int(integ.get("bytes_excluding_module_descriptors",-1)):raise AdapterError("TARGET_MODULE_BYTE_COUNT_MISMATCH")
 if treehash!=integ.get("sha256"):raise AdapterError("TARGET_MODULE_TREE_SHA256_MISMATCH")
 return {"target_id":spec["target"],"module_tree_sha256":treehash,"module_file_count":len(rows),"module_bytes":sum(x["bytes"] for x in rows),
         "weight_manifest_sha256":MANIFEST_SHA,"weight_path":spec["weight"],"weight_bytes":spec["bytes"],"weight_sha256":spec["sha"]}
def peak_child_rss():
 try:
  v=int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss);return v*1024 if platform.system()=="Linux" else v
 except Exception:return None
def json_output(text):
 try:
  x=json.loads(text)
  if isinstance(x,dict):return x
 except json.JSONDecodeError:pass
 decoder=json.JSONDecoder()
 for i,c in enumerate(text):
  if c=="{":
   try:x,_=decoder.raw_decode(text[i:])
   except json.JSONDecodeError:continue
   if isinstance(x,dict):return x
 raise AdapterError("MODEL_RUNTIME_DID_NOT_RETURN_JSON_OBJECT")
def execute_task(record,root,timeout_cap=600):
 started=time.monotonic()
 base={"schema":RESULT_SCHEMA,"status":"FAIL_CLOSED","execution_authorized":False,"certification":"NOT_GRANTED","semantic_quality_equivalence":"NOT_ESTABLISHED"}
 try:
  row=normalize(record,root,timeout_cap)
  identity={"domain_id":row["domain_id"],"operation":row["operation"],"input":row["input"],"input_files":row["input_files"],"limits":row["limits"]}
  out={**base,"task_id":row["task_id"],"domain_id":row["domain_id"],"target_id":row.get("target_id"),"operation":row["operation"],"adapter_id":row["adapter_id"],
       "input_sha256":digest_bytes(canonical(identity)),"input_files":row["input_files"],"started_at_utc":utc_now()}
  if row["domain_id"]==PLAN_ONLY["domain"]:
   from cajita_router import build_plan
   plan=build_plan(row["input"]["request_text"],row["input"]["route_command"])
   out.update({"status":"PLAN_ONLY_BLOCKED" if plan.get("status")!="PLAN_READY" else "PLAN_READY_NOT_EXECUTED","plan_status":plan.get("status"),
               "execution_authorized":False,"blockers":plan.get("blockers",[]),"output":plan,"output_sha256":digest_bytes(canonical(plan)),
               "elapsed_seconds":round(time.monotonic()-started,3)})
   return out,3
  spec=ADAPTERS[row["domain_id"]];integrity=verify_integrity(root,row["domain_id"]);entry=root/spec["entry"]
  if entry.is_symlink() or not entry.is_file():raise AdapterError("TASK_ADAPTER_ENTRYPOINT_MISSING")
  env={k:os.environ[k] for k in ("PATH","HOME","LANG","LC_ALL","TMPDIR","SYSTEMROOT","WINDIR") if k in os.environ}
  env.update({"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1","TOKENIZERS_PARALLELISM":"false","HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","PYTHONNOUSERSITE":"1"})
  child=dict(row["input"]);child.update({"operation":row["operation"],"max_new_tokens":row["limits"]["max_new_tokens"]})
  try:p=subprocess.run([sys.executable,str(entry),"--task-json-stdin"],input=json.dumps(child,ensure_ascii=False,sort_keys=True),text=True,
       stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=str(root),env=env,timeout=row["limits"]["timeout_seconds"],check=False,shell=False)
  except subprocess.TimeoutExpired:
   out.update({"status":"FAIL_TIMEOUT","reason":"TASK_EXECUTION_TIMEOUT","integrity":integrity,"peak_rss_bytes":peak_child_rss(),"elapsed_seconds":round(time.monotonic()-started,3)});return out,4
  out.update({"entrypoint_sha256":digest_file(entry),"integrity":integrity,"return_code":p.returncode,"peak_rss_bytes":peak_child_rss(),"elapsed_seconds":round(time.monotonic()-started,3)})
  if p.returncode:
   out.update({"status":"FAIL_MODEL_RUNTIME","reason":"TASK_RUNTIME_NONZERO_EXIT","stderr_sha256":digest_bytes(p.stderr.encode("utf-8",errors="replace"))})
   # CI enables bounded diagnostics only for synthetic fixtures; production requests
   # never echo model stderr/stdout, which may contain user-specific content.
   if os.environ.get("CAJITA_E2E_DIAGNOSTICS") == "1":
    out["diagnostic_stderr_tail"]=p.stderr[-3000:]
    out["diagnostic_stdout_tail"]=p.stdout[-1200:]
   return out,4
  answer=json_output(p.stdout);status=str(answer.get("status",""));text=answer.get("output_text","");tokens=answer.get("generated_token_count")
  if status!="PASS" and not status.startswith("PASS_"):out.update({"status":"FAIL_MODEL_RESULT_STATUS","model_runtime_status":status});return out,4
  if not isinstance(text,str) or (row["domain_id"]!="D03_TRANSCRIPCION" and not text.strip()):out.update({"status":"FAIL_MODEL_OUTPUT_EMPTY"});return out,4
  if isinstance(tokens,bool) or not isinstance(tokens,int) or tokens<1:out.update({"status":"FAIL_MODEL_OUTPUT_EMPTY","reason":"GENERATED_TOKEN_COUNT_MISSING"});return out,4
  out.update({"status":"PASS_FUNCTIONAL_EXECUTION","execution_authorized":True,"model_runtime_status":status,"output_text":text[:8192],
              "output_sha256":digest_bytes(canonical(answer)),"generated_token_count":tokens,"quality_equivalence":"NOT_ESTABLISHED"})
  return out,0
 except (AdapterError,OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
  base.update({"reason":str(exc)[:240],"elapsed_seconds":round(time.monotonic()-started,3)})
  if isinstance(record,dict):
   for k in ("task_id","domain_id","operation"):base[k]=record.get(k)
  return base,2
def read_request(path):
 p=Path(path).expanduser()
 if p.is_symlink() or not p.is_file():raise AdapterError("REQUEST_FILE_MISSING_OR_SYMLINK")
 if p.stat().st_size>1_000_000:raise AdapterError("REQUEST_FILE_TOO_LARGE")
 r=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(r,dict):raise AdapterError("REQUEST_ROOT_MUST_BE_OBJECT")
 return r
def registry_report():
 routing_path=Path(__file__).resolve().parent/"command_subdomain_routing.json"
 if routing_path.is_symlink() or not routing_path.is_file():
  raise AdapterError("CANONICAL_TARGET_ROUTING_MISSING_OR_UNSAFE")
 try:routing=json.loads(routing_path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError) as exc:raise AdapterError("CANONICAL_TARGET_ROUTING_INVALID") from exc
 targets=routing.get("targets")
 if not isinstance(targets,list) or not targets:raise AdapterError("CANONICAL_TARGET_ROUTING_TARGETS_MISSING")
 targets_by_id={}
 for target in targets:
  if not isinstance(target,dict) or not isinstance(target.get("id"),str) or target["id"] in targets_by_id:
   raise AdapterError("CANONICAL_TARGET_ROUTING_ID_INVALID_OR_DUPLICATE")
  targets_by_id[target["id"]]=target
 rows=[]
 registered_target_ids=set()
 for domain,spec in ADAPTERS.items():
  target=targets_by_id.get(spec["target"])
  if target is None or target.get("domain_id")!=domain or target.get("path")!=spec["module"]:
   raise AdapterError("TASK_ADAPTER_TARGET_BINDING_MISMATCH:"+domain)
  if spec["target"] in registered_target_ids:raise AdapterError("TASK_ADAPTER_TARGET_DUPLICATE:"+spec["target"])
  registered_target_ids.add(spec["target"])
  rows.append({"domain_id":domain,"target_id":spec["target"],"operation":spec["op"],"adapter_id":spec["id"],
               "entrypoint":spec["entry"],"input_contract":"JSON_ON_STDIN",
               "integrity_gate":"MODULE_TREE_AND_WEIGHT_SHA256","registration_scope":"SYNTHETIC_TASK_EXECUTION_ONLY",
               "native_smoke":"REQUIRED","semantic_quality_equivalence":"NOT_ESTABLISHED","certification":"NOT_GRANTED"})
 rows.append({"domain_id":PLAN_ONLY["domain"],"operation":PLAN_ONLY["op"],"adapter_id":PLAN_ONLY["id"],
              "execution":"NOT_IMPLEMENTED","status":"PLAN_ONLY_FAIL_CLOSED","target_id":None})
 target_count=len(targets_by_id)
 unregistered_count=target_count-len(registered_target_ids)
 return {"schema":"CAJITA_TASK_ADAPTER_REGISTRY/1.0","model_task_adapter_count":len(ADAPTERS),
         "synthetic_scope_registered_target_count":len(registered_target_ids),"canonical_target_count":target_count,
         "unregistered_target_count":unregistered_count,"execution_contract":"SHELL_FREE_JSON_STDIN_OFFLINE",
         "registered":rows,"pdf_generation":"NOT_REGISTERED",
         "all_21_target_adapters":"REGISTERED" if unregistered_count==0 else "PARTIAL_REGISTRATION_ONLY_NOT_ESTABLISHED",
         "reference_quality_equivalence":"NOT_ESTABLISHED","native_hardware_validation":"REQUIRED",
         "global_certification":"NOT_GRANTED"}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True);sub.add_parser("registry")
 run=sub.add_parser("execute");run.add_argument("--request-json",required=True);run.add_argument("--root",default=str(Path(__file__).resolve().parent));run.add_argument("--timeout",type=int,default=600)
 a=p.parse_args(argv)
 if a.command=="registry":print(json.dumps(registry_report(),ensure_ascii=False,indent=2));return 0
 try:
  root=Path(a.root).resolve(strict=True)
  if not root.is_dir() or not (root/"cajita_weight_materializer.py").is_file():raise AdapterError("RUNTIME_ROOT_INVALID")
  result,code=execute_task(read_request(a.request_json),root,a.timeout);print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True));return code
 except (AdapterError,OSError,ValueError,json.JSONDecodeError) as exc:
  print(json.dumps({"schema":RESULT_SCHEMA,"status":"FAIL_CLOSED","reason":str(exc)[:240],"execution_authorized":False,"certification":"NOT_GRANTED"},ensure_ascii=False,indent=2));return 2
if __name__=="__main__":raise SystemExit(main())
