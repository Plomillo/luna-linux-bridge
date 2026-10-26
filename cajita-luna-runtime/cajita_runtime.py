#!/usr/bin/env python3
"""Cajita de Luna six-domain runtime router; candidate integration, fail-closed."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, subprocess, sys, time
from pathlib import Path

SCHEMA = "CAJITA_SIX_DOMAIN_RUNTIME/1.1"
RAW_STAGING_CAP_BYTES = 1_500_000_000
COMBINED_DISTRIBUTION_CAP_BYTES = 479_000_000
CANDIDATE_ID = "CAJITA_LUNA_RUNTIME_V9_20261023"
MANIFEST_REL = Path("CAJITA_RUNTIME_V1/weights_manifest.json")
MANIFEST_SHA256 = "703fb6b4c278b6111a354951bb7f9faf3721edb0c89b4dda843242e47634039d"
DOMAINS = [
 {"id":"D01_CEREBRO","name":"1. Cerebro","directory":"1. Cerebro","entrypoint":"1. Cerebro/cerebro_180mb_runtime.py","args":["--smoke-test"],"assets":["1. Cerebro/config.json","1. Cerebro/model.safetensors","1. Cerebro/tokenizer.json","1. Cerebro/tokenizer_config.json"],"scope":"GPT-OSS low-rank candidate; smoke is not quality certification."},
 {"id":"D02_ORQUESTACION","name":"2. Orquestación","directory":"2. Orquestación","entrypoint":"2. Orquestación/Orquestador/CLIs/cli_registry.py","args":["--self-test"],"assets":["2. Orquestación/Orquestador/punto.json","2. Orquestación/Orquestador/CLIs/cli_contract.json"],"scope":"CLI registry self-test; does not prove all external CLI tools are installed."},
 {"id":"D03_TRANSCRIPCION","name":"3. Transcripción","directory":"3. Transcripción","entrypoint":"3. Transcripción/lowrank_runtime.py","args":["--smoke-test"],"assets":["3. Transcripción/config.json","3. Transcripción/model.safetensors","3. Transcripción/preprocessor_config.json","3. Transcripción/tokenizer.json"],"scope":"Whisper low-rank candidate; smoke does not certify transcription quality/WER."},
 {"id":"D04_TRADUCTOR_INTELIGENTE","name":"4. Traductor Inteligente","directory":"4. Traductor Inteligente","entrypoint":"4. Traductor Inteligente/Traducción general/lowrank_runtime.py","args":["--smoke-test"],"assets":["4. Traductor Inteligente/Traducción general/config.json","4. Traductor Inteligente/Traducción general/model.safetensors","4. Traductor Inteligente/Traducción general/sentencepiece.bpe.model"],"scope":"SeamlessM4T v2 low-rank candidate; exact shared embedding/output aliases are restored by the compact runtime; smoke tests text generation only."},
 {"id":"D05_INTELIGENCIA_DOCUMENTAL","name":"5. Inteligencia documental","directory":"5. Inteligencia documental","entrypoint":"5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/docling_30mb_runtime_v1.py","args":["--candidate-dir","5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate","--verify-only"],"assets":["5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_manifest.json","5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_weights.bin"],"scope":"Granite Docling candidate; model-load verification, not document OCR/quality certification."},
 {"id":"D06_SISTEMA_INTELIGENTE","name":"6. Sistema Inteligente","directory":"6. Sistema Inteligente","entrypoint":"6. Sistema Inteligente/Análisis Avanzado/lowrank_runtime_v2.py","args":["--smoke-test"],"assets":["6. Sistema Inteligente/Análisis Avanzado/config.json","6. Sistema Inteligente/Análisis Avanzado/model.safetensors","6. Sistema Inteligente/Anti-Alucinaciones/model.onnx"],"scope":"Qwen3 smoke and ONNX file integrity; ONNX inference adapter/dependencies not certified."},
]

def utc():
 return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b""): h.update(chunk)
 return h.hexdigest()
def root_for(value):
 root=Path(value).resolve() if value else Path(__file__).resolve().parent
 missing=[d["directory"] for d in DOMAINS if not (root/d["directory"]).is_dir()]
 if missing: raise RuntimeError("DOMAIN_DIRECTORIES_MISSING:"+",".join(missing))
 return root
def file_for(root, rel):
 p=root/rel
 if p.is_symlink(): raise RuntimeError("SYMLINK_REJECTED:"+rel)
 p=p.resolve(strict=True)
 if not p.is_relative_to(root) or not p.is_file(): raise RuntimeError("INVALID_OR_ESCAPING_FILE:"+rel)
 return p
def manifest_for(root):
 p=file_for(root,str(MANIFEST_REL))
 if sha256(p)!=MANIFEST_SHA256: raise RuntimeError("WEIGHTS_MANIFEST_SHA256_MISMATCH")
 m=json.loads(p.read_text(encoding="utf-8"))
 if m.get("schema")!="CAJITA_SIX_DOMAIN_WEIGHT_MANIFEST/1.0": raise RuntimeError("MANIFEST_SCHEMA_INVALID")
 if m.get("candidate_id") != CANDIDATE_ID: raise RuntimeError("MANIFEST_CANDIDATE_ID_MISMATCH")
 if len(m.get("artifacts",[]))!=6 or int(m.get("artifact_count",-1))!=6: raise RuntimeError("WEIGHT_COUNT_MISMATCH")
 if sum(int(a["bytes"]) for a in m["artifacts"])!=int(m["total_weight_bytes"]): raise RuntimeError("WEIGHT_TOTAL_MISMATCH")
 return m
def package_size(root):
 count=total=0
 for base, dirs, files in os.walk(root,followlinks=False):
  bp=Path(base)
  for name in dirs:
   if (bp/name).is_symlink(): raise RuntimeError("SYMLINK_DIRECTORY_REJECTED:"+str((bp/name).relative_to(root)))
  for name in files:
   p=bp/name
   if p.is_symlink() or not p.is_file(): raise RuntimeError("NON_REGULAR_FILE_REJECTED:"+str(p.relative_to(root)))
   count+=1; total+=p.stat().st_size
 return count,total
def asset_presence(root, rel):
 root=Path(root).resolve()
 p=root/rel
 if p.is_symlink():
  return {"path":rel,"present":False,"representation":"SYMLINK_REFUSED"}
 if p.is_file():
  return {"path":rel,"present":True,"representation":"RAW_FILE","bytes":p.stat().st_size,"sha256":sha256(p)}
 if Path(rel).name=="tokenizer.json":
  manifest_path=root/"CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json"
  if manifest_path.is_symlink():
   return {"path":rel,"present":False,"representation":"COMPRESSED_MANIFEST_SYMLINK_REFUSED"}
  if manifest_path.is_file():
   try:
    import cajita_tokenizer_materializer as tokenizer_materializer
    manifest=tokenizer_materializer.load_tokenizer_manifest(root)
    matches=[row for row in manifest.get("entries",[]) if row.get("source_path")==Path(rel).as_posix()]
    if len(matches)==1 and matches[0].get("packed") is True:
     row=matches[0]
     return {"path":rel,"present":True,"representation":"GZIP_HASH_PINNED_TOKENIZER","bytes":row["source_bytes"],"sha256":row["source_sha256"],"compressed_path":row["compressed_path"],"compressed_bytes":row["compressed_bytes"],"compressed_sha256":row["compressed_sha256"]}
    return {"path":rel,"present":False,"representation":"TOKENIZER_NOT_HASH_PINNED_AS_COMPRESSED"}
   except Exception as exc:
    return {"path":rel,"present":False,"representation":"COMPRESSED_TOKENIZER_VALIDATION_FAILED","validation_error":type(exc).__name__+":"+str(exc)[:240]}
 return {"path":rel,"present":False,"representation":"MISSING"}

def selftest(root):
 domains=[]; missing=[]
 for d in DOMAINS:
  entry=root/d["entrypoint"]
  assets=[asset_presence(root,a) for a in d["assets"]]
  route= (root/d["directory"]).is_dir() and entry.is_file() and not entry.is_symlink() and all(a["present"] for a in assets)
  domains.append({"id":d["id"],"directory_present":(root/d["directory"]).is_dir(),"entrypoint":d["entrypoint"],"entrypoint_present":entry.is_file() and not entry.is_symlink(),"assets":assets,"route_state":"WIRED" if route else "BLOCKED","scope":d["scope"]})
  if not route: missing.append(d["id"])
 try:
  manifest_for(root); manifest_ok=True; manifest_error=None
 except Exception as exc:
  manifest_ok=False; manifest_error=str(exc)
 count,size=package_size(root); capok=size<=RAW_STAGING_CAP_BYTES
 return {"schema":SCHEMA,"operation":"selftest","captured_at_utc":utc(),"candidate_id":CANDIDATE_ID,"root":str(root),"domain_order":[d["id"] for d in DOMAINS],"domain_count":6,"domains":domains,"blocked_domains":missing,"weights_manifest_valid":manifest_ok,"weights_manifest_error":manifest_error,"package_file_count":count,"package_size_bytes":size,"raw_staging_ceiling_bytes":RAW_STAGING_CAP_BYTES,"combined_distribution_cap_bytes":COMBINED_DISTRIBUTION_CAP_BYTES,"combined_distribution_gate":"ENFORCED_BY_FACTORY_AND_G23_NOT_BY_UNPACKED_TREE_SELFTEST","size_gate":"PASS" if capok else "FAIL","functional_equivalence":"NOT_ESTABLISHED","certification":"NOT_GRANTED","status":"PASS" if not missing and manifest_ok and capok else "FAIL"}
KNOWN_INFRASTRUCTURE_TEST_FIXTURES = frozenset({
 "6. Sistema Inteligente/Anti-Alucinaciones/ONNX_RUNTIME_1_29_0_CP311/onnxruntime/datasets/logreg_iris.onnx",
 "6. Sistema Inteligente/Anti-Alucinaciones/ONNX_RUNTIME_1_29_0_CP311/onnxruntime/datasets/mul_1.onnx",
 "6. Sistema Inteligente/Anti-Alucinaciones/ONNX_RUNTIME_1_29_0_CP311/onnxruntime/datasets/sigmoid.onnx",
})
def classify_model_like_paths(found_paths, listed_weight_paths):
 found=set(found_paths); listed=set(listed_weight_paths)
 recognized=sorted(found & KNOWN_INFRASTRUCTURE_TEST_FIXTURES)
 extras=sorted(found-listed-KNOWN_INFRASTRUCTURE_TEST_FIXTURES)
 missing_fixtures=sorted(KNOWN_INFRASTRUCTURE_TEST_FIXTURES-found)
 return {"recognized_infrastructure_fixtures":recognized,"undeclared_model_like_files":extras,"missing_infrastructure_fixtures":missing_fixtures}
def audit(root):
 m=manifest_for(root); listed={a["path"] for a in m["artifacts"]}; found=set()
 for base,dirs,files in os.walk(root,followlinks=False):
  for n in files:
   p=Path(base)/n
   if p.suffix.lower() in {".safetensors",".bin",".onnx",".pt",".gguf"}: found.add(p.relative_to(root).as_posix())
 result=[]
 for a in m["artifacts"]:
  p=file_for(root,a["path"]); actualsize=p.stat().st_size; actualhash=sha256(p)
  result.append({"id":a["id"],"domain_id":a["domain_id"],"path":a["path"],"expected_bytes":a["bytes"],"actual_bytes":actualsize,"expected_sha256":a["sha256"],"actual_sha256":actualhash,"status":"PASS" if actualsize==int(a["bytes"]) and actualhash==a["sha256"] else "FAIL"})
 count,size=package_size(root); capok=size<=RAW_STAGING_CAP_BYTES
 classified=classify_model_like_paths(found,listed)
 extra=classified["undeclared_model_like_files"]; absent=sorted(listed-found); hashok=all(x["status"]=="PASS" for x in result)
 fixture_records=[]
 for rel in classified["recognized_infrastructure_fixtures"]:
  p=file_for(root,rel)
  fixture_records.append({"path":rel,"bytes":p.stat().st_size,"sha256":sha256(p),"classification":"ONNX_RUNTIME_TEST_FIXTURE_NOT_CAJITA_WEIGHT","integrity":"COVERED_BY_MATERIALIZED_MODULE_TREE_HASH"})
 passed=hashok and not extra and not absent and not classified["missing_infrastructure_fixtures"] and capok
 return {"schema":SCHEMA,"operation":"audit-weights","captured_at_utc":utc(),"candidate_id":CANDIDATE_ID,"artifacts":result,"artifact_count":len(result),"total_weight_bytes":sum(x["actual_bytes"] for x in result),"undeclared_model_like_files":extra,"recognized_infrastructure_test_fixtures":fixture_records,"missing_infrastructure_test_fixtures":classified["missing_infrastructure_fixtures"],"missing_manifest_files":absent,"package_file_count":count,"package_size_bytes":size,"raw_staging_ceiling_bytes":RAW_STAGING_CAP_BYTES,"combined_distribution_cap_bytes":COMBINED_DISTRIBUTION_CAP_BYTES,"combined_distribution_gate":"ENFORCED_BY_FACTORY_AND_G23_NOT_BY_UNPACKED_TREE_AUDIT","size_gate":"PASS" if capok else "FAIL","weight_presence_integrity":"PASS" if passed else "FAIL","functional_equivalence":"NOT_ESTABLISHED","independent_validation":"NOT_RUN","certification":"NOT_GRANTED","promotion":"NOT_AUTHORIZED","status":"PASS" if passed and capok else "FAIL"}
def select_domain(value):
 aliases={}
 for i,d in enumerate(DOMAINS,1):
  aliases[d["id"].casefold()]=d; aliases[str(i)]=d
  aliases[d["name"].casefold()]=d
  aliases[d["name"].split(". ",1)[-1].casefold()]=d
 aliases.update({"orquestacion":DOMAINS[1],"orquestación":DOMAINS[1],"transcripcion":DOMAINS[2],"transcripción":DOMAINS[2],"traductor":DOMAINS[3],"documental":DOMAINS[4],"sistema":DOMAINS[5]})
 try: return aliases[value.strip().casefold()]
 except KeyError as exc: raise ValueError("UNKNOWN_DOMAIN:"+value) from exc
def choose_python(root, domain):
 if domain["id"] == "D02_ORQUESTACION":
  return sys.executable, "standard-library"
 required = ("torch", "numpy", "transformers", "safetensors")
 configured = os.environ.get("CAJITA_PYTHON")
 candidates = []
 if configured:
  candidates.append((Path(configured).expanduser(), "CAJITA_PYTHON"))
 else:
  for ancestor in (root, *root.parents):
   candidate = ancestor / "state/tools/venvs/llama-cpp-b10819-py313/bin/python"
   if candidate.is_file():
    candidates.append((candidate, "discovered-CUSTOSZ-model-venv"))
  candidates.append((Path(sys.executable), "runtime-interpreter"))
 seen = set()
 failures = []
 probe_code = "import importlib.util,sys; req=('torch','numpy','transformers','safetensors'); missing=[x for x in req if importlib.util.find_spec(x) is None]; print('MISSING='+','.join(missing)); sys.exit(1 if missing else 0)"
 for candidate, source in candidates:
  try:
   # Preserve the venv executable path: resolving its symlink to /usr/bin/python
   # discards the virtual-environment context and its installed packages.
   candidate = Path(os.path.abspath(os.path.expanduser(str(candidate))))
   candidate_key = os.path.normcase(str(candidate))
   if candidate_key in seen: continue
   seen.add(candidate_key)
   if not candidate.is_file() or (os.name != "nt" and not os.access(candidate, os.X_OK)):
    failures.append(str(candidate)+":not-executable"); continue
   probe = subprocess.run([str(candidate), "-B", "-c", probe_code], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12, check=False)
   if probe.returncode == 0:
    return str(candidate), source
   failures.append(str(candidate)+":"+(probe.stdout.strip() or probe.stderr.strip())[:250])
  except Exception as exc:
   failures.append(str(candidate)+":"+type(exc).__name__+":"+str(exc)[:150])
 raise RuntimeError("MODEL_PYTHON_ENVIRONMENT_NOT_READY; set CAJITA_PYTHON to a Python with torch,numpy,transformers,safetensors; "+ " | ".join(failures))

def smoke(root,d,timeout):
 entry=file_for(root,d["entrypoint"])
 interpreter, env_source = choose_python(root,d)
 argv=[interpreter,"-B",str(entry),*d["args"]]
 env=os.environ.copy()
 env.update({"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1",
             "NUMEXPR_NUM_THREADS":"1","TOKENIZERS_PARALLELISM":"false",
             "HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1"})
 print(json.dumps({"schema":SCHEMA,"operation":"smoke-start","domain_id":d["id"],"argv":argv,
                   "python_environment_source":env_source,"timeout_seconds":timeout,
                   "offline_mode":True,"certification":"NOT_GRANTED"},ensure_ascii=False),flush=True)
 t=time.monotonic()
 try: p=subprocess.run(argv,cwd=str(root),env=env,check=False,timeout=timeout)
 except subprocess.TimeoutExpired:
  print(json.dumps({"domain_id":d["id"],"status":"TIMEOUT","timeout_seconds":timeout,"certification":"NOT_GRANTED"}),flush=True); return 124
 code=p.returncode
 print(json.dumps({"schema":SCHEMA,"operation":"smoke-result","domain_id":d["id"],"return_code":code,
                   "elapsed_seconds":round(time.monotonic()-t,3),"status":"PASS" if code==0 else "FAIL",
                   "python_environment_source":env_source,"quality_equivalence":"NOT_ESTABLISHED",
                   "certification":"NOT_GRANTED"},ensure_ascii=False),flush=True)
 return code

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument("command",choices=("status","selftest","audit-weights","smoke","smoke-all","routes","plan","execute-task","materialize-asset"))
 ap.add_argument("--root"); ap.add_argument("--domain"); ap.add_argument("--timeout",type=int,default=600)
 ap.add_argument("--request"); ap.add_argument("--route-command"); ap.add_argument("--trace-file"); ap.add_argument("--request-json"); ap.add_argument("--asset-id")
 a=ap.parse_args()
 if a.command=="execute-task":
  if not a.request_json: ap.error("execute-task requires --request-json")
  from cajita_task_adapters import main as task_adapter_main
  return task_adapter_main(["execute","--root",str(root_for(a.root)),"--request-json",a.request_json,"--timeout",str(a.timeout)])
 if a.command in {"routes","plan"}:
  from cajita_router import main as router_main
  router_args=[a.command]
  if a.command=="plan":
   if not a.request: ap.error("plan requires --request")
   router_args.extend(["--request",a.request])
   if a.route_command: router_args.extend(["--route-command",a.route_command])
   if a.trace_file: router_args.extend(["--trace-file",a.trace_file])
  return router_main(router_args)
 try:
  root=root_for(a.root)
  if not 1<=a.timeout<=7200: raise ValueError("TIMEOUT_OUT_OF_RANGE")
  if a.command=="materialize-asset":
   if not a.asset_id: raise ValueError("MATERIALIZE_ASSET_ID_REQUIRED")
   from cajita_externalized_packaging import materialize_asset
   result=materialize_asset(root,a.asset_id)
   print(json.dumps(result,indent=2,ensure_ascii=False))
   return 0
  if a.command in {"status","selftest"}:
   r=selftest(root); r["operation"]=a.command
   print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["status"]=="PASS" else 2
  if a.command=="audit-weights":
   r=audit(root); print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["status"]=="PASS" else 2
  if a.command=="smoke":
   if not a.domain: ap.error("smoke requires --domain (1..6 or domain id)")
   return smoke(root,select_domain(a.domain),a.timeout)
  results=[]
  for d in DOMAINS: results.append({"domain_id":d["id"],"return_code":smoke(root,d,a.timeout)})
  ok=all(x["return_code"]==0 for x in results)
  print(json.dumps({"schema":SCHEMA,"operation":"smoke-all-summary","results":results,"status":"PASS" if ok else "FAIL","certification":"NOT_GRANTED"},indent=2))
  return 0 if ok else 3
 except Exception as exc:
  print(json.dumps({"schema":SCHEMA,"status":"FAIL_CLOSED","error_type":type(exc).__name__,"reason":str(exc)[:1000],"certification":"NOT_GRANTED"},indent=2,ensure_ascii=False),file=sys.stderr)
  return 2
if __name__=="__main__": raise SystemExit(main())

