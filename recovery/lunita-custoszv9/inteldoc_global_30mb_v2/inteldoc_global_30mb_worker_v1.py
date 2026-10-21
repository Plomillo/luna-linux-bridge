#!/usr/bin/env python3
"""CUSTOSZ V9 global Intelligent Documental optimizer. Originals are immutable."""
from __future__ import annotations
import argparse,copy,datetime as dt,hashlib,json,os,pathlib,shutil,subprocess,sys,tarfile,tempfile,uuid

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
PROJECT=HOME/"Proyectos/1. PROYECTOS PRIORITARIOS/1. PROYECTO LUNA/2. Cajita de Luna"
DOC=PROJECT/"5. Inteligencia documental"
OP=HOME/"Proyectos/1. PROYECTOS PRIORITARIOS/5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
CONT=OP/"CUSTOSZ_CONTINUITY_V1"; STATE=CONT/"state"
LANE=STATE/"jobs/inteldoc_global_30mb_lane_v1"; OLD_LANE=STATE/"jobs/docling_30mb_lane_v1"
OLD_QUANTIZER=OLD_LANE/"docling_30mb_quantize_worker_v1.py"; OLD_RUNTIME=OLD_LANE/"docling_30mb_runtime_v1.py"
PYTHON=CONT/"state/tools/venvs/llama-cpp-b10819-py313/bin/python"
MISSION_ID="CUSTOSZV9_INTELDOC_GLOBAL_30MB_V2"; CAP=30_000_000
PINS={
 "granite_docling_q4_gguf":("Docling/granite-docling-258M-Q4_K_M.gguf",138559520,"4ba41a480d2b6594613a23819df8fcc382d9dab9691e28bf327b3ac799fe0a82"),
 "granite_docling_mmproj_f16":("Docling/mmproj-granite-docling-258M-f16.gguf",190031712,"4b7b2c4ed3162bd9cb323668c188e2324838b8f8ca4f3f9767f16c4c600d43ad"),
 "docling_slim_wheel":("Docling/docling_slim-2.124.0-py3-none-any.whl",780430,"2c7c667394d3eae9080bc15143ed6f1d39a4838090d9e3f29be212606e6676bd"),
 "calibre_binary_reference":("Calibre/calibre-9.14.0-x86_64.txz",192898432,"7f53a0863ed6d32407bc72053b966e39d5b64813f2592bd9c741504c01c0e7f3"),
 "calibre_source_reference":("Calibre/calibre-9.14.0.tar.xz",48867616,"d1bc24024b0942429c627e9c5d0b25d51df9c1af1e1d8dca3e572f03b194c561")}
def utc(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open("rb") as f:
  for b in iter(lambda:f.read(4*1024*1024),b""): h.update(b)
 return h.hexdigest()
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def atomic(p,obj):
 p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True,mode=0o700); tmp=p.with_name(p.name+"."+uuid.uuid4().hex+".tmp")
 with tmp.open("x",encoding="utf-8") as f: json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
 os.chmod(tmp,0o600); os.replace(tmp,p)
def tree_bytes(p): return sum(f.stat().st_size for f in pathlib.Path(p).rglob("*") if f.is_file())
def ev(jdir,typ,payload):
 p=pathlib.Path(jdir)/"events.jsonl"; seq=1; prev="0"*64
 if p.exists():
  for line in p.read_text(encoding="utf-8").splitlines():
   x=json.loads(line); seq=x["sequence"]+1; prev=x["event_sha256"]
 x={"sequence":seq,"timestamp_utc":utc(),"mission_id":MISSION_ID,"event_type":typ,"payload":payload,"previous_event_sha256":prev}
 x["event_sha256"]=hashlib.sha256(canon(x)).hexdigest()
 with p.open("a",encoding="utf-8") as f: f.write(json.dumps(x,sort_keys=True,ensure_ascii=False)+"\n"); f.flush(); os.fsync(f.fileno())
def phase(jdir,name,status="RUNNING",**kw):
 x={"schema":"INTELDOC_GLOBAL_30MB_PROGRESS/1.0","mission_id":MISSION_ID,"updated_at_utc":utc(),"phase":name,"status":status,"hard_cap_bytes":CAP,"original_sources_modified":False,"runtime_smoke":"DEFERRED_BY_USER_UNTIL_ALL_ARTIFACTS_QUANTIZED","canonical_promotion":"NOT_AUTHORIZED","certification":"NOT_GRANTED"}; x.update(kw); atomic(pathlib.Path(jdir)/"progress.json",x); ev(jdir,"PHASE_UPDATED",{"phase":name,"status":status,**kw}); return x
def inventory():
 out={}
 for k,(rel,n,h) in PINS.items():
  p=DOC/rel
  if not p.is_file() or p.stat().st_size!=n or sha(p)!=h: raise RuntimeError("SOURCE_PIN_MISMATCH:"+rel)
  out[k]={"path":str(p),"bytes":n,"sha256":h,"read_only":True}
 return out
def tar_profile(p):
 count=0; total=0; largest=[]
 with tarfile.open(p,"r:xz") as t:
  for m in t:
   count+=1
   if m.isfile(): total+=m.size; largest.append((m.size,m.name))
 return {"archive_bytes":p.stat().st_size,"member_count":count,"expanded_regular_bytes":total,"largest_members":[{"path":n,"bytes":s} for s,n in sorted(largest,reverse=True)[:12]]}
def patch_quantizer():
 LANE.mkdir(parents=True,exist_ok=True,mode=0o700); shutil.copy2(OLD_RUNTIME,LANE/"docling_30mb_runtime_v1.py")
 s=OLD_QUANTIZER.read_text(encoding="utf-8")
 swaps=[
 ('JOB=STATE/"jobs/docling_30mb_lane_v1"','JOB=STATE/"jobs/inteldoc_global_30mb_lane_v1"'),
 ('WORKER_STATE=STATE/"jobs/docling_30mb_worker_v1"','WORKER_STATE=STATE/"jobs/inteldoc_global_30mb_worker_v1/docling_component_run"'),
 ('CANDIDATES=STATE/"cajita_candidates"','CANDIDATES=STATE/"jobs/inteldoc_global_30mb_worker_v1/components"'),
 ('MISSION_ID="CUSTOSZV9_DOCLING_INTELIGENCIA_DOCUMENTAL_30MB_BIVLM_NQ_V1"','MISSION_ID="CUSTOSZV9_INTELDOC_GLOBAL_30MB_V2"'),
 ('TEXT_RANK_FRACTION=0.20','TEXT_RANK_FRACTION=0.02'),
 ('EMBED_RANK_FRACTION=0.16','EMBED_RANK_FRACTION=0.025'),
 ('VISION_OUTLIER_FRACTION=0.00005','VISION_OUTLIER_FRACTION=0.000005'),
 ('DOCILING_GRANITE_DOCLING_MODEL_BUNDLE_ONLY; Calibre and docling_slim remain separate registered resources, not silently removed or represented as included','COMPONENT_ONLY; global bundle and dependency charges enforced by parent worker')]
 for old,new in swaps:
  if old not in s: raise RuntimeError("QUANTIZER_ANCHOR_MISSING:"+old[:70])
  s=s.replace(old,new,1)
 a=s.find('  vendor=jdir/"vendor_pillow"; pillow=ensure_pillow(vendor)')
 b=s.find(' except Exception as e:',a)
 if a<0 or b<0: raise RuntimeError("SMOKE_DEFER_PATCH_ANCHOR_MISSING")
 repl='''  # User explicitly deferred all functional smoke tests until all artifacts are quantized.
  final=CANDIDATES/cand_id
  if final.exists(): raise RuntimeError("COMPONENT_CANDIDATE_COLLISION")
  fm=json.loads((stage/"quantized_manifest.json").read_text(encoding="utf-8"))
  fm["published_component_candidate_path"]=str(final)
  fm["hard_cap_scope"]="COMPONENT_ONLY; parent worker applies the global gross budget"
  fm["runtime_startup_smoke"]={"status":"DEFERRED_BY_USER","reason":"Run after all Intelligence Documental artifacts have been quantized"}
  atomic(stage/"quantized_manifest.json",fm)
  final_size=tree_bytes(stage)
  if final_size>CAP: raise RuntimeError("COMPONENT_SIZE_GATE_FAILURE:"+str(final_size))
  final.parent.mkdir(parents=True,exist_ok=True,mode=0o700); os.replace(stage,final)
  final_size=tree_bytes(final)
  receipt.update({"phase":"COMPONENT_QUANTIZATION_COMPLETE","status":"QUANTIZED_PENDING_GLOBAL_BUDGET","finished_at_utc":utc(),
    "published_component_candidate_path":str(final),"candidate_bundle_bytes":final_size,"size_gate":"PASS_COMPONENT_ONLY",
    "runtime_smoke":"DEFERRED_BY_USER","startup_certification":"NOT_GRANTED","model_quality_certification":"NOT_GRANTED",
    "quality_equivalence":"NOT_ESTABLISHED","canonical_promotion":"NOT_AUTHORIZED","source_files_modified":False})
  atomic(jdir/"progress.json",receipt)
  out=STATE/"worker_outputs"/("INTELDOC_GLOBAL_DOCLING_COMPONENT_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".json")
  atomic(out,receipt)
  event(jdir,"DOCLING_COMPONENT_QUANTIZATION_COMPLETE_SMOKE_DEFERRED",{"candidate_path":str(final),"bytes":final_size,
    "settings":fm.get("settings"),"global_budget":"NOT_YET_EVALUATED","smoke_test":"DEFERRED_BY_USER"})
  print(json.dumps(receipt,indent=2,ensure_ascii=False),flush=True)
  return 0
'''
 s=s[:a]+repl+s[b:]
 out=LANE/"docling_global_aggressive_quantizer_v1.py"; out.write_text(s,encoding="utf-8"); os.chmod(out,0o600)
 q=subprocess.run([str(PYTHON),"-B","-m","py_compile",str(out)],capture_output=True,text=True,timeout=30)
 if q.returncode: raise RuntimeError("PATCHED_QUANTIZER_COMPILE_FAIL:"+q.stderr[-1000:])
 return out,sha(out)
def keep_member(name):
 n=name.lstrip("./")
 if n in ("resources/localization/locales.zip","resources/qtwebengine_devtools_resources.pak"): return False
 if n.startswith("translations/qtwebengine_locales/") and pathlib.PurePosixPath(n).name not in {"en-US.pak","en-GB.pak","es.pak","es-419.pak"}: return False
 if n.startswith(("docs/","doc/","man/","tests/","test/","examples/","include/")) or "/share/doc/" in "/"+n: return False
 if n.endswith((".1",".1.gz",".pyc",".pyo")) or "/__pycache__/" in "/"+n: return False
 return True
def minimize_calibre(src_path,out_path,tempdir):
 strip=shutil.which("strip")
 stats={"source_bytes":src_path.stat().st_size,"members_seen":0,"members_kept":0,"members_removed":0,"removed_expanded_bytes":0,"elf_seen":0,"elf_strip_savings_bytes":0,"strip_failures":0,"strip_available":bool(strip)}
 tempdir.mkdir(parents=True,exist_ok=True,mode=0o700); out_path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 with tarfile.open(src_path,"r:xz") as inp, tarfile.open(out_path,"w:xz",preset=9) as out:
  for m in inp:
   stats["members_seen"]+=1
   if not keep_member(m.name):
    stats["members_removed"]+=1
    if m.isfile(): stats["removed_expanded_bytes"]+=m.size
    continue
   if m.isdir() or m.issym() or m.islnk(): out.addfile(m); stats["members_kept"]+=1; continue
   if not m.isfile(): continue
   src=inp.extractfile(m)
   if src is None: continue
   bn=pathlib.PurePosixPath(m.name).name
   likely=m.name.startswith(("lib/","plugins/","bin/","libexec/")) and (".so" in bn or "." not in bn)
   tmp=None
   try:
    if likely and m.size>32768:
     tmp=tempdir/("elf_"+uuid.uuid4().hex)
     with tmp.open("wb") as f: shutil.copyfileobj(src,f,1024*1024)
     with tmp.open("rb") as f: iself=f.read(4)==b"\x7fELF"
     if iself:
      stats["elf_seen"]+=1; old=tmp.stat().st_size
      if strip:
       z=subprocess.run([strip,"--strip-unneeded",str(tmp)],capture_output=True,text=True,timeout=120,check=False)
       if z.returncode!=0: stats["strip_failures"]+=1
      stats["elf_strip_savings_bytes"]+=max(0,old-tmp.stat().st_size)
     info=copy.copy(m); info.size=tmp.stat().st_size
     with tmp.open("rb") as f: out.addfile(info,f)
    else: out.addfile(m,src)
   finally:
    src.close()
    if tmp:
     try: tmp.unlink()
     except FileNotFoundError: pass
   stats["members_kept"]+=1
 stats["candidate_archive_bytes"]=out_path.stat().st_size; stats["candidate_sha256"]=sha(out_path)
 return stats
def dependency_charge():
 site=pathlib.Path(sys.prefix)/"lib/python3.13/site-packages"
 names=("torch","transformers","safetensors","numpy","PIL","tokenizers","huggingface_hub","filelock","fsspec","packaging","yaml","regex","requests","tqdm","sympy","networkx","jinja2","typing_extensions","mpmath","markupsafe","certifi","urllib3","idna","charset_normalizer")
 paths=[]; total=0
 if not site.is_dir(): return {"status":"UNRESOLVED","site_packages":str(site),"charged_bytes":None,"paths":[]}
 for n in names:
  found=set()
  for pat in (n,n+".dist-info",n+"-*.dist-info",n.replace("_","-")+"-*.dist-info"):
   found.update(site.glob(pat))
  for p in sorted(found):
   if not p.exists(): continue
   size=sum(x.stat().st_size for x in p.rglob("*") if x.is_file()) if p.is_dir() else p.stat().st_size
   paths.append({"path":str(p),"bytes":size}); total+=size
 pyexe=pathlib.Path(sys.executable)
 if pyexe.is_file(): paths.append({"path":str(pyexe),"bytes":pyexe.stat().st_size}); total+=pyexe.stat().st_size
 stdlib=pathlib.Path(sys.base_prefix)/"lib/python3.13"
 if stdlib.is_dir():
  size=sum(x.stat().st_size for x in stdlib.rglob("*") if x.is_file())
  paths.append({"path":str(stdlib),"bytes":size}); total+=size
 return {"status":"MEASURED","site_packages":str(site),"charged_bytes":total,"paths":paths}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--run",action="store_true"); ap.add_argument("--job-dir",default=str(WORKER_ROOT)); a=ap.parse_args()
 if not a.run: ap.error("explicit --run required")
 jdir=pathlib.Path(a.job_dir).resolve(); jdir.mkdir(parents=True,exist_ok=True,mode=0o700); lock=jdir/"worker.lock"
 fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600); os.write(fd,str(os.getpid()).encode()); os.fsync(fd); os.close(fd)
 started=utc(); stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"); stage=jdir/("candidate_staging_"+stamp); stage.mkdir(parents=True,exist_ok=False,mode=0o700)
 try:
  phase(jdir,"GLOBAL_INVENTORY",original_source_count=5,started_at_utc=started,stage=str(stage))
  src=inventory(); binprofile=tar_profile(DOC/"Calibre/calibre-9.14.0-x86_64.txz"); sourceprofile=tar_profile(DOC/"Calibre/calibre-9.14.0.tar.xz")
  ev(jdir,"SOURCE_INVENTORY_HASHES_PASS",{"sources":src,"calibre_binary_profile":binprofile,"calibre_source_profile":sourceprofile})
  phase(jdir,"DOCLING_AGGRESSIVE_QUANTIZATION",source_inventory=src,calibre_binary_expanded_bytes=binprofile["expanded_regular_bytes"],calibre_source_expanded_bytes=sourceprofile["expanded_regular_bytes"])
  qscript,qhash=patch_quantizer(); childdir=WORKER_ROOT/"docling_component_run"; childdir.mkdir(parents=True,exist_ok=True,mode=0o700)
  with (jdir/"docling_quantizer.log").open("ab") as log:
   child=subprocess.run([str(PYTHON),"-B",str(qscript),"--run","--job-dir",str(childdir)],stdout=log,stderr=subprocess.STDOUT,check=False,timeout=None)
  cp=json.loads((childdir/"progress.json").read_text(encoding="utf-8"))
  if child.returncode!=0 or cp.get("status")!="QUANTIZED_PENDING_GLOBAL_BUDGET":
   raise RuntimeError("DOCLING_REQUANTIZATION_HELD:"+json.dumps({"returncode":child.returncode,"progress":cp},ensure_ascii=False)[:2000])
  doccandidate=pathlib.Path(cp["published_component_candidate_path"])
  phase(jdir,"CALIBRE_MINIMAL_REPACK",docling_candidate_path=str(doccandidate),docling_candidate_bytes=cp.get("candidate_bundle_bytes"),quantizer_sha256=qhash)
  bundle=stage/"operational_bundle"; bundle.mkdir(parents=True,exist_ok=False,mode=0o700)
  shutil.copytree(doccandidate,bundle/"docling_model")
  wheelsrc=DOC/"Docling/docling_slim-2.124.0-py3-none-any.whl"; shutil.copy2(wheelsrc,bundle/wheelsrc.name)
  stats=minimize_calibre(DOC/"Calibre/calibre-9.14.0-x86_64.txz",bundle/"calibre/calibre-9.14.0-core-minimized.txz",stage/"strip_tmp")
  shutil.rmtree(stage/"strip_tmp",ignore_errors=True)
  phase(jdir,"GLOBAL_GROSS_BUDGET_GATE",calibre_candidate_bytes=stats["candidate_archive_bytes"],calibre_stats=stats,docling_candidate_bytes=tree_bytes(bundle/"docling_model"),wheel_bytes=wheelsrc.stat().st_size)
  deps=dependency_charge()
  manifest={"schema":"INTELDOC_GLOBAL_OPERATIONAL_BUNDLE/1.0","mission_id":MISSION_ID,"created_at_utc":utc(),"hard_cap_bytes":CAP,
   "hard_cap_scope":"Gross sum of the combined Docling model/assets/package, minimized Calibre runtime, manifest/metadata, and required runtime dependency charge.",
   "source_inventory":src,"source_originals_modified":False,
   "components":{"docling_model":{"path":"docling_model","bytes":tree_bytes(bundle/"docling_model"),"settings":json.loads((doccandidate/"quantized_manifest.json").read_text()).get("settings"),"smoke_test":"DEFERRED_BY_USER"},
    "docling_slim_wheel":{"path":wheelsrc.name,"bytes":wheelsrc.stat().st_size},"calibre_runtime":{"path":"calibre/calibre-9.14.0-core-minimized.txz",**stats}},
   "required_runtime_dependencies":deps,"runtime_dependencies_bundled":False,"dependency_charge_explanation":"Runtime package bytes are explicitly charged even though the existing host environment is not copied into the portable candidate.",
   "functional_tests":"DEFERRED_BY_USER_UNTIL_ALL_ARTIFACTS_QUANTIZED","certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
  atomic(bundle/"GLOBAL_MANIFEST.json",manifest)
  payload=tree_bytes(bundle); charged=None if deps["charged_bytes"] is None else payload+deps["charged_bytes"]
  manifest["gross_bundle_payload_bytes"]=payload; manifest["runtime_dependency_charge_bytes"]=deps["charged_bytes"]; manifest["gross_charged_total_bytes"]=charged
  manifest["over_cap_bytes"]=None if charged is None else max(0,charged-CAP)
  manifest["global_size_gate"]="PASS" if charged is not None and charged<=CAP and payload<=CAP else "HOLD_OVER_CAP_OR_DEPENDENCY_UNRESOLVED"
  atomic(bundle/"GLOBAL_MANIFEST.json",manifest); payload=tree_bytes(bundle); charged=None if deps["charged_bytes"] is None else payload+deps["charged_bytes"]
  result={"schema":"INTELDOC_GLOBAL_30MB_RESULT/1.0","mission_id":MISSION_ID,"finished_at_utc":utc(),
   "status":"CANDIDATE_READY_FOR_LATER_TESTS" if charged is not None and charged<=CAP and payload<=CAP else "HOLD_OVER_CAP_OR_DEPENDENCY_UNRESOLVED",
   "phase":"GLOBAL_GROSS_BUDGET_GATE","hard_cap_bytes":CAP,"bundle_payload_bytes":payload,"runtime_dependency_charge_bytes":deps["charged_bytes"],
   "gross_charged_total_bytes":charged,"over_cap_bytes":None if charged is None else max(0,charged-CAP),"candidate_bundle_path":str(bundle),
   "docling_component_bytes":tree_bytes(bundle/"docling_model"),"docling_tensor_count":cp.get("source_tensor_count"),"docling_quantization_status":cp.get("status"),
   "calibre_candidate_archive_bytes":stats["candidate_archive_bytes"],"calibre_members_removed":stats["members_removed"],"calibre_expanded_bytes_removed":stats["removed_expanded_bytes"],
   "elf_strip_savings_bytes":stats["elf_strip_savings_bytes"],"functional_tests":"DEFERRED_BY_USER","original_sources_modified":False,
   "quality_equivalence":"NOT_ESTABLISHED","certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
  atomic(jdir/"result.json",result); ev(jdir,"GLOBAL_SIZE_GATE_RECORDED",result)
  phase(jdir,"GLOBAL_GROSS_BUDGET_GATE",result["status"],result_path=str(jdir/"result.json"),bundle_payload_bytes=payload,runtime_dependency_charge_bytes=deps["charged_bytes"],gross_charged_total_bytes=charged)
  print(json.dumps(result,indent=2,ensure_ascii=False),flush=True)
  return 0 if result["status"]=="CANDIDATE_READY_FOR_LATER_TESTS" else 4
 except Exception as e:
  r={"schema":"INTELDOC_GLOBAL_30MB_RESULT/1.0","mission_id":MISSION_ID,"finished_at_utc":utc(),"status":"HOLD","phase":"HELD_OR_FAILED","error":type(e).__name__+":"+str(e),"candidate_staging_path":str(stage),"original_sources_modified":False,"functional_tests":"DEFERRED_BY_USER","certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
  atomic(jdir/"result.json",r)
  try: ev(jdir,"GLOBAL_WORKER_HELD",{"error":r["error"],"stage":str(stage)})
  except Exception: pass
  print(json.dumps(r,indent=2,ensure_ascii=False),file=sys.stderr,flush=True)
  raise
 finally:
  try:
   if lock.exists() and int(lock.read_text().strip())==os.getpid(): lock.unlink()
  except Exception: pass
if __name__=="__main__": raise SystemExit(main())
