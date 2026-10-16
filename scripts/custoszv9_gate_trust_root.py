#!/usr/bin/env python3
"""Protected V9 assurance logic. Reports only bounded, digest-bound tested scope."""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess,sys,zipfile
from pathlib import Path

SCOPE="CUSTOSZV9_CRFU_AND_EXACT_V8_BYTE_PRESERVATION_SUBSCOPE"
def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
 return h.hexdigest()
def single(root:Path,name:str)->Path:
 found=list(root.rglob(name))
 if len(found)!=1:raise ValueError("MISSING_OR_AMBIGUOUS_FILE:"+name)
 return found[0]
def read_json(path:Path)->dict:
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict):raise ValueError("JSON_ROOT_NOT_OBJECT:"+str(path))
 return value
def write(path:Path,value:dict)->None:
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def g22(a:argparse.Namespace)->int:
 out=Path(a.out);fail=[]
 commit=a.candidate_sha
 if not re.fullmatch(r"[0-9a-f]{40}",commit):fail.append("CANDIDATE_COMMIT_SHA_INVALID")
 package=single(Path(a.candidate_dir),"CUSTOSZV9.pyz")
 report=read_json(single(Path(a.candidate_dir),"custoszv9-build-report.json"))
 log=single(Path(a.candidate_dir),"custoszv9-unit-tests.log").read_text(encoding="utf-8",errors="replace")
 repro=read_json(single(Path(a.candidate_dir),"custoszv9-reproducibility.json"))
 source_baseline=Path(a.trusted_source)/"CUSTOSZV8.pyz"
 candidate_baseline=Path(a.candidate_source)/"CUSTOSZV8.pyz"
 if not source_baseline.is_file() or not candidate_baseline.is_file():fail.append("TRACKED_V8_BASELINE_MISSING")
 with zipfile.ZipFile(package,"r") as z:
  if z.testzip() is not None:fail.append("V9_ZIP_CRC_FAILURE")
  names=z.namelist()
  required={"custoszv9/data/CUSTOSZV8.pyz","custoszv9/data/build_manifest.json",
    "custoszv8/core.py","custoszv8/cli.py","custoszv9/crfu/coordinator.py","custoszv9/crfu/selftest.py"}
  if not required.issubset(set(names)):fail.append("REQUIRED_PACKAGE_MEMBERS_MISSING")
  manifest=json.loads(z.read("custoszv9/data/build_manifest.json"))
  embedded=z.read("custoszv9/data/CUSTOSZV8.pyz")
  embedded_sha=hashlib.sha256(embedded).hexdigest()
 if report.get("source_commit")!=commit or manifest.get("source_commit")!=commit:fail.append("SOURCE_COMMIT_BINDING_MISMATCH")
 if report.get("status")!="PASS_BUILD_ONLY_NOT_CERTIFIED":fail.append("BUILD_REPORT_STATUS_INVALID")
 if report.get("package_sha256")!=sha(package):fail.append("PACKAGE_DIGEST_REPORT_MISMATCH")
 if report.get("package_size_bytes")!=package.stat().st_size:fail.append("PACKAGE_SIZE_REPORT_MISMATCH")
 if report.get("embedded_baseline_byte_exact") is not True or report.get("baseline_unchanged") is not True:fail.append("BASELINE_PRESERVATION_NOT_PROVEN")
 if manifest.get("baseline",{}).get("sha256")!=embedded_sha or len(embedded)!=99400:fail.append("EMBEDDED_BASELINE_IDENTITY_FAILURE")
 if source_baseline.is_file() and candidate_baseline.is_file():
  if sha(source_baseline)!=sha(candidate_baseline):fail.append("CANDIDATE_BASELINE_DIFFERS_FROM_TRUSTED_BASELINE")
  if sha(source_baseline)!=embedded_sha:fail.append("EMBEDDED_BASELINE_DIFFERS_FROM_TRUSTED_MAIN")
 if repro.get("status")!="PASS" or repro.get("same_source_commit_two_builds") is not True:fail.append("REPRODUCIBILITY_NOT_PASS")
 if repro.get("first_sha256")!=sha(package) or repro.get("second_sha256")!=sha(package):fail.append("REPRODUCIBILITY_DIGEST_MISMATCH")
 if not re.search(r"^\s*Ran\s+\d+\s+tests?\s+in\s+",log,re.M) or not re.search(r"^\s*OK\s*$",log,re.M):fail.append("UNIT_TEST_LOG_NOT_PASS")
 if manifest.get("governance",{}).get("G23")!="NOT_GRANTED" or manifest.get("governance",{}).get("G24")!="NOT_GRANTED":fail.append("FALSE_CERTIFICATION_IN_MANIFEST")
 if manifest.get("formal_assurance",{}).get("toolchain_executed") is not False:fail.append("FORMAL_TOOLCHAIN_STATUS_OVERCLAIMED")
 value={"schema":"CUSTOSZV9_G22_TESTED_SCOPE/1.0","candidate_commit_sha":commit,
   "candidate_package_sha256":sha(package),"candidate_package_size_bytes":package.stat().st_size,
   "v8_baseline_sha256":embedded_sha,"v8_baseline_size_bytes":len(embedded),
   "trusted_workflow_sha":a.trusted_workflow_sha,"producer_identity":"CUSTOSZV9_BUILD_WORKFLOW",
   "evaluator_identity":"CUSTOSZV9_G22_TRUST_ROOT","scope":SCOPE,
   "status":"PASS" if not fail else "FAIL","failures":fail,
   "canonical_global_non_regression":"HOLD_NOT_FULLY_EVALUATED",
   "formal_correspondence":"NOT_PROVEN","PUAC2_operational_scope":"HOLD",
   "release_eligible":False,"certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
 write(out,value);print(json.dumps(value,indent=2));return 0 if not fail else 2
def g23(a:argparse.Namespace)->int:
 fail=[];root=Path(a.candidate_dir);commit=a.candidate_sha;package=single(root,"CUSTOSZV9.pyz");pkgsha=sha(package)
 g22r=read_json(Path(a.g22))
 if g22r.get("status")!="PASS":fail.append("G22_TESTED_SCOPE_NOT_PASS")
 if g22r.get("candidate_commit_sha")!=commit:fail.append("G22_CANDIDATE_COMMIT_MISMATCH")
 if g22r.get("candidate_package_sha256")!=pkgsha:fail.append("G22_PACKAGE_DIGEST_MISMATCH")
 if g22r.get("trusted_workflow_sha")!=a.trusted_workflow_sha:fail.append("TRUST_ROOT_SHA_MISMATCH")
 # Execute candidate in this isolated, read-only, secret-free job; impose a hard timeout per command.
 import os
 env={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"HOME":os.environ.get("RUNNER_TEMP","/tmp"),"LANG":"C.UTF-8","PYTHONNOUSERSITE":"1"}
 commands=[
  ("version",[sys.executable,"-I",str(package),"--version"]),
  ("crfu-status",[sys.executable,"-I",str(package),"crfu","status"]),
  ("crfu-selftest",[sys.executable,"-I",str(package),"crfu","selftest"]),
  ("v8-selftest",[sys.executable,"-I",str(package),"selftest"]),
  ("v8-status",[sys.executable,"-I",str(package),"status"]),
 ]
 results=[]
 for name,cmd in commands:
  try:
   p=subprocess.run(cmd,capture_output=True,text=True,timeout=60,env=env,cwd=str(Path(a.candidate_dir).resolve()))
   passed=p.returncode==0
   item={"name":name,"returncode":p.returncode,"status":"PASS" if passed else "FAIL",
         "stdout_sha256":hashlib.sha256(p.stdout.encode()).hexdigest(),"stderr_sha256":hashlib.sha256(p.stderr.encode()).hexdigest()}
   if not passed:item["stderr_tail"]=p.stderr[-1000:];fail.append("INDEPENDENT_COMMAND_FAILED:"+name)
   if name=="crfu-selftest" and passed:
    try:
     payload=json.loads(p.stdout); 
     if payload.get("status")!="PASS":fail.append("CRFU_SELFTEST_REPORT_NOT_PASS")
    except ValueError:fail.append("CRFU_SELFTEST_OUTPUT_INVALID")
   results.append(item)
  except (OSError,subprocess.TimeoutExpired) as exc:
   results.append({"name":name,"status":"FAIL","error":type(exc).__name__});fail.append("INDEPENDENT_COMMAND_EXCEPTION:"+name)
 value={"schema":"CUSTOSZV9_G23_INDEPENDENT_VALIDATION/1.0","candidate_commit_sha":commit,
   "candidate_package_sha256":pkgsha,"candidate_package_size_bytes":package.stat().st_size,
   "g22_record_sha256":sha(Path(a.g22)),"trusted_workflow_sha":a.trusted_workflow_sha,
   "producer_identity":"CUSTOSZV9_BUILD_WORKFLOW","validator_identity":"CUSTOSZV9_G23_TRUSTED_WORKFLOW",
   "scope":SCOPE,"independent_execution_results":results,"status":"PASS" if not fail else "FAIL",
   "failures":fail,"certification_authorization_for_g24":not fail,
   "canonical_G23_status":"HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN","PUAC2_status":"HOLD",
   "release_eligible":False,"activation_authorized":False}
 write(Path(a.out),value);print(json.dumps(value,indent=2));return 0 if not fail else 2
def g24(a:argparse.Namespace)->int:
 fail=[];root=Path(a.candidate_dir);package=single(root,"CUSTOSZV9.pyz");pkgsha=sha(package)
 g22r=read_json(Path(a.g22));g23r=read_json(Path(a.g23))
 if g22r.get("status")!="PASS":fail.append("G22_TESTED_SCOPE_NOT_PASS")
 if g23r.get("status")!="PASS" or g23r.get("certification_authorization_for_g24") is not True:fail.append("G23_NOT_PASS_OR_NOT_AUTHORIZING")
 for label,row in (("G22",g22r),("G23",g23r)):
  if row.get("candidate_commit_sha")!=a.candidate_sha:fail.append(label+"_COMMIT_MISMATCH")
  if row.get("candidate_package_sha256")!=pkgsha:fail.append(label+"_PACKAGE_DIGEST_MISMATCH")
  if row.get("trusted_workflow_sha")!=a.trusted_workflow_sha:fail.append(label+"_TRUST_ROOT_MISMATCH")
 if g23r.get("g22_record_sha256")!=sha(Path(a.g22)):fail.append("G23_G22_RECORD_HASH_MISMATCH")
 if g23r.get("validator_identity")==g23r.get("producer_identity"):fail.append("G23_IDENTITY_NOT_DISTINCT")
 if not re.fullmatch(r"[0-9a-f]{40}",a.trusted_workflow_sha):fail.append("TRUSTED_WORKFLOW_SHA_INVALID")
 valid=not fail
 cert={"schema":"CUSTOSZV9_G24_SCOPED_DECISION/1.0","candidate_commit_sha":a.candidate_sha,
   "candidate_package_sha256":pkgsha,"candidate_package_size_bytes":package.stat().st_size,
   "g22_record_sha256":sha(Path(a.g22)),"g23_record_sha256":sha(Path(a.g23)),
   "trusted_workflow_sha":a.trusted_workflow_sha,"producer_identity":"CUSTOSZV9_BUILD_WORKFLOW",
   "validator_identity":"CUSTOSZV9_G23_TRUSTED_WORKFLOW","certifier_identity":"CUSTOSZV9_G24_TRUSTED_WORKFLOW",
   "tested_scope":SCOPE,"decision":"PASS_FOR_TESTED_SUBSCOPE" if valid else "DENIED",
   "failures":fail,"full_canonical_G01_G24_status":"HOLD","PUAC2_C25_C32_status":"HOLD_NOT_CANONICALLY_ADMITTED",
   "PUAC2_operational_host_mTLS_rollback_status":"HOLD_UNTIL_REQUIRED_HOST_EVIDENCE_AND_ED25519_SIGNATURES_VERIFY",
   "formal_toolchain_and_HoTT_status":"NOT_PROVEN",
   "full_release_eligible":False,"operational_authorization":"NOT_GRANTED","active_authorized":False,
   "canonical_admission":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED","certification_propagation":False,
   "warning":"This digest-bound automated decision covers only the listed software test subscope; it is not full CUSTOSZV9 certification or PUAC2 operational certification."}
 write(Path(a.out),cert);print(json.dumps(cert,indent=2));return 0 if valid else 2
def main()->int:
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest="gate",required=True)
 for name in ("g22","g23","g24"):
  q=sub.add_parser(name);q.add_argument("--candidate-dir",required=True);q.add_argument("--candidate-sha",required=True);q.add_argument("--trusted-workflow-sha",required=True);q.add_argument("--out",required=True)
  if name=="g22":q.add_argument("--candidate-source",required=True);q.add_argument("--trusted-source",required=True)
  if name=="g23":q.add_argument("--g22",required=True)
  if name=="g24":q.add_argument("--g22",required=True);q.add_argument("--g23",required=True)
 a=p.parse_args()
 try:return {"g22":g22,"g23":g23,"g24":g24}[a.gate](a)
 except Exception as exc:
  payload={"schema":"CUSTOSZV9_GATE_FAILURE/1.0","gate":a.gate,"status":"HOLD","release_eligible":False,"reason":type(exc).__name__+":"+str(exc)}
  write(Path(a.out),payload);print(json.dumps(payload,indent=2));return 2
if __name__=="__main__":raise SystemExit(main())
