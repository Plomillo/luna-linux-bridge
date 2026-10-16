#!/usr/bin/env python3
"""Trusted CUSTOSZ V9 assurance helpers; all decisions bind the exact commit and package digest.

The G23 private key is used only in a separate attestation job after candidate code has
finished executing. G24 verifies G23's Ed25519 signature and signs a decision; this
implementation deliberately emits HOLD for full canonical/PUAC2 release until its
separate required evidence is available and valid.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,os,re,subprocess,sys,zipfile
from datetime import datetime,timezone
from pathlib import Path

SCOPE="CUSTOSZV9_CRFU_AND_EXACT_V8_BYTE_PRESERVATION_SUBSCOPE"
MAX_CANDIDATE_PACKAGE_BYTES=20*1024*1024
MAX_ARCHIVE_MEMBERS=4096
MAX_ARCHIVE_MEMBER_BYTES=16*1024*1024
MAX_ARCHIVE_TOTAL_UNCOMPRESSED_BYTES=64*1024*1024
G22_SCHEMA="CUSTOSZV9_G22_TESTED_SCOPE/1.0"
G23_UNSIGNED_SCHEMA="CUSTOSZV9_G23_UNSIGNED_VALIDATION/1.0"
SIGNED_SCHEMA="CUSTOSZV9_ED25519_ATTESTATION/1.0"
G24_PAYLOAD_SCHEMA="CUSTOSZV9_G24_DECISION/2.0"
CANONICAL_PROMOTION_BLOCKERS=[
 "PROTECTED_V25_BASELINE_NOT_AVAILABLE_FOR_EXACT_BYTE_COMPARISON_IN_REPOSITORY",
 "COMPLETE_CANONICAL_G01_G24_APPLICABILITY_MATRIX_NOT_INDEPENDENTLY_ESTABLISHED",
 "PUAC2_C25_C32_REMAIN_LOCAL_CONTROLS_PENDING_CANONICAL_ADMISSION",
 "FORMAL_TOOLCHAIN_AND_MODEL_IMPLEMENTATION_CORRESPONDENCE_NOT_PROVEN",
 "CANONICAL_OPERATIONAL_AUTHORIZATION_NOT_GRANTED",
]

def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as stream:
  for block in iter(lambda:stream.read(1024*1024),b""):h.update(block)
 return h.hexdigest()
def sha_bytes(data:bytes)->str:
 return hashlib.sha256(data).hexdigest()
def canonical_bytes(value:dict)->bytes:
 return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def utc_now()->str:
 return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def is_commit(value:object)->bool:
 return isinstance(value,str) and re.fullmatch(r"[0-9a-f]{40}",value) is not None
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

def _crypto_types():
 try:
  from cryptography.hazmat.primitives import serialization
  from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
 except ImportError as exc:
  raise RuntimeError("CRYPTOGRAPHY_REQUIRED_FOR_TRUSTED_ATTESTATION") from exc
 return serialization,Ed25519PrivateKey,Ed25519PublicKey
def _load_private(pem:str):
 if not isinstance(pem,str) or not pem.strip():raise ValueError("ED25519_PRIVATE_KEY_NOT_CONFIGURED")
 serialization,private_type,_=_crypto_types()
 try:key=serialization.load_pem_private_key(pem.encode("utf-8"),password=None)
 except Exception as exc:raise ValueError("ED25519_PRIVATE_KEY_UNREADABLE") from exc
 if not isinstance(key,private_type):raise ValueError("SIGNING_KEY_NOT_ED25519")
 return key
def _load_public(pem:str):
 if not isinstance(pem,str) or not pem.strip():raise ValueError("ED25519_PUBLIC_KEY_NOT_CONFIGURED")
 serialization,_,public_type=_crypto_types()
 try:key=serialization.load_pem_public_key(pem.encode("utf-8"))
 except Exception as exc:raise ValueError("ED25519_PUBLIC_KEY_UNREADABLE") from exc
 if not isinstance(key,public_type):raise ValueError("VERIFICATION_KEY_NOT_ED25519")
 return key
def _raw_public(key)->bytes:
 serialization,private_type,public_type=_crypto_types()
 public=key.public_key() if isinstance(key,private_type) else key
 if not isinstance(public,public_type):raise ValueError("KEY_NOT_ED25519")
 return public.public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
def public_key_sha256(pem:str)->str:
 return sha_bytes(_raw_public(_load_public(pem)))
def sign_record(payload:dict,private_pem:str,signer_identity:str)->dict:
 if not isinstance(payload,dict):raise ValueError("SIGNED_PAYLOAD_NOT_OBJECT")
 if not isinstance(signer_identity,str) or not signer_identity.strip():raise ValueError("SIGNER_IDENTITY_NOT_CONFIGURED")
 key=_load_private(private_pem)
 payload_bytes=canonical_bytes(payload)
 signature=base64.b64encode(key.sign(payload_bytes)).decode("ascii")
 return {"schema":SIGNED_SCHEMA,"algorithm":"Ed25519","signer_identity":signer_identity,
         "signer_public_key_sha256":sha_bytes(_raw_public(key)),
         "payload_sha256":sha_bytes(payload_bytes),"signature_b64":signature,"payload":payload}
def verify_signed_record(record:dict,public_pem:str,expected_signer:str,forbidden_identities:tuple[str,...]=())->tuple[dict|None,list[str]]:
 failures=[]
 if not isinstance(record,dict):return None,["SIGNED_ATTESTATION_NOT_OBJECT"]
 if record.get("schema")!=SIGNED_SCHEMA:failures.append("SIGNED_ATTESTATION_SCHEMA_INVALID")
 if record.get("algorithm")!="Ed25519":failures.append("SIGNED_ATTESTATION_ALGORITHM_INVALID")
 if not expected_signer or record.get("signer_identity")!=expected_signer:failures.append("SIGNED_ATTESTATION_SIGNER_IDENTITY_MISMATCH")
 if record.get("signer_identity") in forbidden_identities:failures.append("SIGNED_ATTESTATION_SIGNER_NOT_DISTINCT")
 payload=record.get("payload")
 if not isinstance(payload,dict):return None,failures+["SIGNED_ATTESTATION_PAYLOAD_MISSING"]
 payload_bytes=canonical_bytes(payload)
 if record.get("payload_sha256")!=sha_bytes(payload_bytes):failures.append("SIGNED_ATTESTATION_PAYLOAD_HASH_MISMATCH")
 try:
  public=_load_public(public_pem)
  if record.get("signer_public_key_sha256")!=sha_bytes(_raw_public(public)):
   failures.append("SIGNED_ATTESTATION_PUBLIC_KEY_FINGERPRINT_MISMATCH")
  signature=record.get("signature_b64")
  if not isinstance(signature,str):failures.append("SIGNED_ATTESTATION_SIGNATURE_MISSING")
  else:
   try:
    public.verify(base64.b64decode(signature,validate=True),payload_bytes)
   except Exception:failures.append("ED25519_SIGNATURE_INVALID")
 except Exception as exc:
  failures.append(type(exc).__name__+":"+str(exc))
 return (payload if not failures else None),sorted(set(failures))
def public_keys_match(private_pem:str,public_pem:str)->bool:
 return _raw_public(_load_private(private_pem))==_raw_public(_load_public(public_pem))
EXPECTED_G23_COMMANDS={"version","crfu-status","crfu-selftest","v8-selftest","v8-status"}
def g23_report_consistency(payload:dict)->tuple[bool,list[str]]:
 errors=[]
 rows=payload.get("independent_execution_results")
 failures=payload.get("failures")
 if not isinstance(rows,list):return False,["G23_EXECUTION_RESULTS_NOT_LIST"]
 observed_names=[row.get("name") for row in rows if isinstance(row,dict)]
 if len(rows)!=len(EXPECTED_G23_COMMANDS) or set(observed_names)!=EXPECTED_G23_COMMANDS or len(set(observed_names))!=len(observed_names):
  errors.append("G23_REQUIRED_COMMAND_SET_MISMATCH")
 for row in rows:
  if not isinstance(row,dict):errors.append("G23_COMMAND_RESULT_NOT_OBJECT");continue
  if row.get("status") not in {"PASS","FAIL"}:errors.append("G23_COMMAND_STATUS_INVALID")
  if isinstance(row.get("returncode"),bool) or not isinstance(row.get("returncode"),int):errors.append("G23_COMMAND_RETURN_CODE_INVALID")
  for field in ("stdout_sha256","stderr_sha256"):
   if not isinstance(row.get(field),str) or re.fullmatch(r"[0-9a-f]{64}",row[field]) is None:
    errors.append("G23_COMMAND_OUTPUT_HASH_INVALID:"+field)
  if row.get("status")=="PASS" and row.get("returncode")!=0:errors.append("G23_COMMAND_PASS_RETURN_CODE_NONZERO")
 if not isinstance(failures,list):errors.append("G23_FAILURE_LIST_INVALID");failures=[]
 observed_pass=not errors and not failures and len(rows)==len(EXPECTED_G23_COMMANDS) and all(
  isinstance(row,dict) and row.get("status")=="PASS" and row.get("returncode")==0 for row in rows)
 expected_result="PASS" if observed_pass else "FAIL"
 if payload.get("tested_scope_result")!=expected_result:errors.append("G23_TESTED_SCOPE_RESULT_NOT_DERIVED_FROM_EVIDENCE")
 if payload.get("scoped_decision_admissible") is not observed_pass:errors.append("G23_SCOPE_ADMISSIBILITY_NOT_DERIVED_FROM_EVIDENCE")
 return observed_pass,sorted(set(errors))

def g22(a:argparse.Namespace)->int:
 fail=[];commit=a.candidate_sha
 if not is_commit(commit):fail.append("CANDIDATE_COMMIT_SHA_INVALID")
 package=single(Path(a.candidate_dir),"CUSTOSZV9.pyz")
 report=read_json(single(Path(a.candidate_dir),"custoszv9-build-report.json"))
 log=single(Path(a.candidate_dir),"custoszv9-unit-tests.log").read_text(encoding="utf-8",errors="replace")
 repro=read_json(single(Path(a.candidate_dir),"custoszv9-reproducibility.json"))
 source_baseline=Path(a.trusted_source)/"CUSTOSZV8.pyz"
 candidate_baseline=Path(a.candidate_source)/"CUSTOSZV8.pyz"
 if not source_baseline.is_file() or not candidate_baseline.is_file():fail.append("TRACKED_V8_BASELINE_MISSING")
 if source_baseline.is_symlink() or candidate_baseline.is_symlink():fail.append("V8_BASELINE_SYMLINK_FORBIDDEN")
 try:
  if not candidate_baseline.resolve().is_relative_to(Path(a.candidate_source).resolve()):
   fail.append("CANDIDATE_BASELINE_ESCAPES_SOURCE_CHECKOUT")
 except OSError:
  fail.append("CANDIDATE_BASELINE_PATH_UNRESOLVED")
 if not is_commit(a.trusted_workflow_sha):fail.append("TRUSTED_WORKFLOW_SHA_INVALID")
 if package.stat().st_size>MAX_CANDIDATE_PACKAGE_BYTES:fail.append("CANDIDATE_PACKAGE_SIZE_LIMIT_EXCEEDED")
 with zipfile.ZipFile(package,"r") as z:
  infos=z.infolist();names=[item.filename for item in infos]
  if len(infos)>MAX_ARCHIVE_MEMBERS:fail.append("ZIP_MEMBER_COUNT_LIMIT_EXCEEDED")
  if len(set(names))!=len(names):fail.append("DUPLICATE_ZIP_MEMBER_NAMES")
  if sum(item.file_size for item in infos)>MAX_ARCHIVE_TOTAL_UNCOMPRESSED_BYTES:fail.append("ZIP_TOTAL_UNCOMPRESSED_LIMIT_EXCEEDED")
  if any(item.file_size>MAX_ARCHIVE_MEMBER_BYTES for item in infos):fail.append("ZIP_MEMBER_SIZE_LIMIT_EXCEEDED")
  if any(item.flag_bits&1 for item in infos):fail.append("ENCRYPTED_ZIP_MEMBER_FORBIDDEN")
  if z.testzip() is not None:fail.append("V9_ZIP_CRC_FAILURE")
  required={"custoszv9/data/CUSTOSZV8.pyz","custoszv9/data/build_manifest.json","custoszv8/core.py",
    "custoszv8/cli.py","custoszv9/crfu/coordinator.py","custoszv9/crfu/selftest.py","custoszv9/crfu/puac2.py"}
  if not required.issubset(set(names)):fail.append("REQUIRED_PACKAGE_MEMBERS_MISSING")
  manifest=json.loads(z.read("custoszv9/data/build_manifest.json"))
  embedded=z.read("custoszv9/data/CUSTOSZV8.pyz");embedded_sha=sha_bytes(embedded)
 if report.get("source_commit")!=commit or manifest.get("source_commit")!=commit:fail.append("SOURCE_COMMIT_BINDING_MISMATCH")
 if report.get("status")!="PASS_BUILD_ONLY_NOT_CERTIFIED":fail.append("BUILD_REPORT_STATUS_INVALID")
 if report.get("package_sha256")!=sha(package):fail.append("PACKAGE_DIGEST_REPORT_MISMATCH")
 if report.get("package_size_bytes")!=package.stat().st_size:fail.append("PACKAGE_SIZE_REPORT_MISMATCH")
 if report.get("embedded_baseline_byte_exact") is not True or report.get("baseline_unchanged") is not True:fail.append("BASELINE_PRESERVATION_NOT_PROVEN")
 if manifest.get("baseline",{}).get("sha256")!=embedded_sha or len(embedded)!=99400:fail.append("EMBEDDED_BASELINE_IDENTITY_FAILURE")
 if source_baseline.is_file() and candidate_baseline.is_file():
  if sha(source_baseline)!=sha(candidate_baseline):fail.append("CANDIDATE_BASELINE_DIFFERS_FROM_TRUSTED_BASELINE")
  if sha(source_baseline)!=embedded_sha:fail.append("EMBEDDED_BASELINE_DIFFERS_FROM_TRUSTED_MAIN")
 authority_digests={}
 for name in ("Louksna.md","PUAC2.md"):
  trusted_path=Path(a.trusted_source)/name;candidate_path=Path(a.candidate_source)/name
  if not trusted_path.is_file() or not candidate_path.is_file():
   fail.append("CANONICAL_SOURCE_FILE_MISSING:"+name);continue
  trusted_digest=sha(trusted_path);candidate_digest=sha(candidate_path)
  authority_digests[name]={"trusted_sha256":trusted_digest,"candidate_sha256":candidate_digest,
                           "byte_identical":trusted_digest==candidate_digest}
  if trusted_digest!=candidate_digest:fail.append("CANONICAL_SOURCE_BYTE_DRIFT:"+name)
 protected_v25_present=(Path(a.trusted_source)/"LUNACORE_final_formalized_v25.md").is_file()
 if repro.get("status")!="PASS" or repro.get("same_source_commit_two_builds") is not True:fail.append("REPRODUCIBILITY_NOT_PASS")
 if repro.get("source_commit")!=commit or repro.get("first_sha256")!=sha(package) or repro.get("second_sha256")!=sha(package):fail.append("REPRODUCIBILITY_DIGEST_OR_COMMIT_MISMATCH")
 if not re.search(r"^\s*Ran\s+\d+\s+tests?\s+in\s+",log,re.M) or not re.search(r"^\s*OK\s*$",log,re.M):fail.append("UNIT_TEST_LOG_NOT_PASS")
 if manifest.get("governance",{}).get("G23")!="NOT_GRANTED" or manifest.get("governance",{}).get("G24")!="NOT_GRANTED":fail.append("FALSE_CERTIFICATION_IN_MANIFEST")
 if manifest.get("formal_assurance",{}).get("toolchain_executed") is not False:fail.append("FORMAL_TOOLCHAIN_STATUS_OVERCLAIMED")
 value={"schema":G22_SCHEMA,"candidate_commit_sha":commit,"candidate_package_sha256":sha(package),
   "candidate_package_size_bytes":package.stat().st_size,"v8_baseline_sha256":embedded_sha,
   "v8_baseline_size_bytes":len(embedded),"trusted_workflow_sha":a.trusted_workflow_sha,
   "producer_identity":"CUSTOSZV9_BUILD_WORKFLOW","evaluator_identity":"CUSTOSZV9_G22_TRUST_ROOT",
   "scope":SCOPE,"checked_at_utc":utc_now(),
   "status":"PASS_FOR_DECLARED_SCOPE" if not fail else "FAIL",
   "tested_scope_result":"PASS" if not fail else "FAIL","failures":fail,
   "canonical_source_digests":authority_digests,"protected_v25_baseline_present":protected_v25_present,
   "canonical_global_non_regression":"HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN","formal_correspondence":"NOT_PROVEN",
   "local_puac_controls_status":"EVALUATED_FOR_DECLARED_SCOPE_ONLY",
   "release_eligible":False,"canonical_promotion":"NOT_AUTHORIZED"}
 write(Path(a.out),value);print(json.dumps(value,indent=2));return 0 if not fail else 2

def g23(a:argparse.Namespace)->int:
 fail=[];root=Path(a.candidate_dir);commit=a.candidate_sha;package=single(root,"CUSTOSZV9.pyz");pkgsha=sha(package)
 g22r=read_json(Path(a.g22))
 if g22r.get("schema")!=G22_SCHEMA or g22r.get("tested_scope_result")!="PASS":fail.append("G22_TESTED_SCOPE_NOT_PASS")
 if g22r.get("candidate_commit_sha")!=commit:fail.append("G22_CANDIDATE_COMMIT_MISMATCH")
 if g22r.get("candidate_package_sha256")!=pkgsha:fail.append("G22_PACKAGE_DIGEST_MISMATCH")
 if g22r.get("trusted_workflow_sha")!=a.trusted_workflow_sha:fail.append("TRUST_ROOT_SHA_MISMATCH")
 validator_id=a.validator_id
 if not isinstance(validator_id,str) or not validator_id.strip():fail.append("G23_VALIDATOR_ID_NOT_CONFIGURED")
 if validator_id in ("CUSTOSZV9_BUILD_WORKFLOW","CUSTOSZV9_G22_TRUST_ROOT"):fail.append("G23_IDENTITY_NOT_DISTINCT")
 # Candidate is executed without tokens, private keys, or inherited environment variables.
 import os
 env={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"HOME":os.environ.get("RUNNER_TEMP","/tmp"),
      "LANG":"C.UTF-8","PYTHONNOUSERSITE":"1","PYTHONDONTWRITEBYTECODE":"1"}
 commands=[("version",[sys.executable,"-I",str(package),"--version"]),
  ("crfu-status",[sys.executable,"-I",str(package),"crfu","status"]),
  ("crfu-selftest",[sys.executable,"-I",str(package),"crfu","selftest"]),
  ("v8-selftest",[sys.executable,"-I",str(package),"selftest"]),
  ("v8-status",[sys.executable,"-I",str(package),"status"])]
 results=[]
 for name,cmd in commands:
  try:
   p=subprocess.run(cmd,capture_output=True,text=True,timeout=60,env=env,cwd=str(Path(a.candidate_dir).resolve()))
   passed=p.returncode==0
   item={"name":name,"returncode":p.returncode,"status":"PASS" if passed else "FAIL",
         "stdout_sha256":sha_bytes(p.stdout.encode()),"stderr_sha256":sha_bytes(p.stderr.encode())}
   if not passed:item["stderr_tail"]=p.stderr[-1000:];fail.append("INDEPENDENT_COMMAND_FAILED:"+name)
   if name=="crfu-selftest" and passed:
    try:
     result=json.loads(p.stdout)
     if result.get("status")!="PASS":fail.append("CRFU_SELFTEST_REPORT_NOT_PASS")
    except ValueError:fail.append("CRFU_SELFTEST_OUTPUT_INVALID")
   results.append(item)
  except (OSError,subprocess.TimeoutExpired) as exc:
   results.append({"name":name,"status":"FAIL","error":type(exc).__name__});fail.append("INDEPENDENT_COMMAND_EXCEPTION:"+name)
 value={"schema":G23_UNSIGNED_SCHEMA,"candidate_commit_sha":commit,"candidate_package_sha256":pkgsha,
   "candidate_package_size_bytes":package.stat().st_size,"g22_record_sha256":sha(Path(a.g22)),
   "trusted_workflow_sha":a.trusted_workflow_sha,"producer_identity":"CUSTOSZV9_BUILD_WORKFLOW",
   "validator_identity":validator_id,"scope":SCOPE,"checked_at_utc":utc_now(),
   "independent_execution_results":results,"status":"PASS_FOR_DECLARED_SCOPE" if not fail else "FAIL",
   "tested_scope_result":"PASS" if not fail else "FAIL","validation_completed":True,
   "failures":sorted(set(fail)),"scoped_decision_admissible":not fail,
   "canonical_G23_status":"HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN",
   "local_puac_controls_status":g22r.get("local_puac_controls_status","UNKNOWN"),
   "PUAC2_status":"LOCAL_SCOPE_EVALUATED_NOT_CANONICALLY_ADMITTED",
   "release_eligible":False,"activation_authorized":False}
 write(Path(a.out),value);print(json.dumps(value,indent=2))
 # Exit 0 means a complete machine-readable report exists. Its tested_scope_result is the outcome.
 return 0

def g23_sign(a:argparse.Namespace)->int:
 unsigned=read_json(Path(a.g23_unsigned));g22r=read_json(Path(a.g22))
 package=single(Path(a.candidate_dir),"CUSTOSZV9.pyz");pkgsha=sha(package)
 identity=os.environ.get("PUAC2_G23_VALIDATOR_ID","")
 private_pem=os.environ.get("PUAC2_G23_SIGNING_PRIVATE_KEY_PEM","")
 public_pem=os.environ.get("PUAC2_G23_PUBLIC_KEY_PEM","")
 fail=[]
 if unsigned.get("schema")!=G23_UNSIGNED_SCHEMA:fail.append("G23_UNSIGNED_REPORT_SCHEMA_INVALID")
 if unsigned.get("status")!="HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN" or unsigned.get("tested_scope_result") not in {"PASS","FAIL"} or unsigned.get("validation_completed") is not True:fail.append("G23_UNSIGNED_RESULT_INVALID")
 _,consistency_errors=g23_report_consistency(unsigned)
 fail.extend(consistency_errors)
 if unsigned.get("candidate_commit_sha")!=a.candidate_sha:fail.append("G23_CANDIDATE_COMMIT_MISMATCH")
 if unsigned.get("candidate_package_sha256")!=pkgsha:fail.append("G23_PACKAGE_DIGEST_MISMATCH")
 if unsigned.get("g22_record_sha256")!=sha(Path(a.g22)):fail.append("G23_G22_RECORD_HASH_MISMATCH")
 if g22r.get("tested_scope_result")!="PASS" or g22r.get("candidate_commit_sha")!=a.candidate_sha or g22r.get("candidate_package_sha256")!=pkgsha:fail.append("G22_REPORT_NOT_VALID_FOR_SIGNING")
 if unsigned.get("validator_identity")!=identity or not identity:fail.append("G23_VALIDATOR_ID_MISMATCH_OR_MISSING")
 if identity in (unsigned.get("producer_identity"),"CUSTOSZV9_G22_TRUST_ROOT"):fail.append("G23_IDENTITY_NOT_DISTINCT")
 if unsigned.get("trusted_workflow_sha")!=a.trusted_workflow_sha:fail.append("G23_TRUST_ROOT_SHA_MISMATCH")
 if fail:raise ValueError("G23_SIGNING_REFUSED:"+",".join(sorted(set(fail))))
 if not public_keys_match(private_pem,public_pem):raise ValueError("G23_PRIVATE_PUBLIC_KEY_MISMATCH")
 record=sign_record(unsigned,private_pem,identity)
 payload,errors=verify_signed_record(record,public_pem,identity,(unsigned.get("producer_identity",""),))
 if errors or payload!=unsigned:raise ValueError("G23_SELF_VERIFICATION_FAILED:"+",".join(errors))
 write(Path(a.out),record)
 print(json.dumps({"status":"SIGNED_G23_REPORT","candidate_commit_sha":a.candidate_sha,
  "candidate_package_sha256":pkgsha,"signer_identity":identity,
  "payload_sha256":record["payload_sha256"],"public_key_sha256":record["signer_public_key_sha256"],
  "underlying_g23_status":unsigned.get("status"),"underlying_g23_tested_scope_result":unsigned.get("tested_scope_result"),"signature":"VERIFIED"},indent=2))
 return 0

def g24(a:argparse.Namespace)->int:
 root=Path(a.candidate_dir);package=single(root,"CUSTOSZV9.pyz");pkgsha=sha(package);commit=a.candidate_sha
 g22r=read_json(Path(a.g22));g23r=read_json(Path(a.g23));fail=[]
 verification_path=Path(a.g23_attestation_verification)
 if not verification_path.is_file() or verification_path.stat().st_size==0:
  fail.append("G23_GITHUB_ATTESTATION_VERIFICATION_EVIDENCE_MISSING")
 if g22r.get("schema")!=G22_SCHEMA or g22r.get("tested_scope_result")!="PASS":
  fail.append("G22_TESTED_SCOPE_NOT_PASS")
 if g22r.get("candidate_commit_sha")!=commit:fail.append("G22_COMMIT_MISMATCH")
 if g22r.get("candidate_package_sha256")!=pkgsha:fail.append("G22_PACKAGE_DIGEST_MISMATCH")
 if g22r.get("trusted_workflow_sha")!=a.trusted_workflow_sha:fail.append("G22_TRUST_ROOT_MISMATCH")
 if g23r.get("schema")!=G23_UNSIGNED_SCHEMA:fail.append("G23_SCHEMA_INVALID")
 if g23r.get("tested_scope_result")!="PASS" or g23r.get("scoped_decision_admissible") is not True:
  fail.append("G23_TESTED_SCOPE_NOT_PASS_OR_NOT_ADMISSIBLE")
 if g23r.get("candidate_commit_sha")!=commit:fail.append("G23_COMMIT_MISMATCH")
 if g23r.get("candidate_package_sha256")!=pkgsha:fail.append("G23_PACKAGE_DIGEST_MISMATCH")
 if g23r.get("trusted_workflow_sha")!=a.trusted_workflow_sha:fail.append("G23_TRUST_ROOT_MISMATCH")
 if g23r.get("g22_record_sha256")!=sha(Path(a.g22)):fail.append("G23_G22_RECORD_HASH_MISMATCH")
 _,consistency_errors=g23_report_consistency(g23r)
 fail.extend("G23_EVIDENCE_INCONSISTENT:"+issue for issue in consistency_errors)
 g22_scope_pass=(g22r.get("tested_scope_result")=="PASS" and not g22r.get("failures"))
 g23_scope_pass=(g23r.get("tested_scope_result")=="PASS" and not g23r.get("failures"))
 certified=not fail and g22_scope_pass and g23_scope_pass
 decision="CERTIFIED_FOR_DECLARED_STANDALONE_SOFTWARE_SCOPE" if certified else "HOLD"
 # This scope certificate never grants canonical admission, activation, or promotion.
 payload={"schema":"CUSTOSZV9_SOFTWARE_SCOPE_CERTIFICATE/1.0",
  "decision":decision,"package_scope_certified":certified,
  "candidate_commit_sha":commit,"candidate_package_sha256":pkgsha,
  "candidate_package_size_bytes":package.stat().st_size,"scope":SCOPE,
  "g22_record_sha256":sha(Path(a.g22)),"g23_record_sha256":sha(Path(a.g23)),
  "g23_attestation_verification_sha256":sha(verification_path) if verification_path.is_file() else None,
  "trusted_workflow_sha":a.trusted_workflow_sha,
  "producer_identity":"CUSTOSZV9_BUILD_WORKFLOW",
  "independent_validator_identity":g23r.get("validator_identity"),
  "certifier_identity":"CUSTOSZV9_G24_GITHUB_ATTESTED_WORKFLOW_JOB",
  "g22_tested_scope_result":g22r.get("tested_scope_result"),
  "g23_tested_scope_result":g23r.get("tested_scope_result"),
  "failures":sorted(set(fail)),
  "local_puac_control_status":"EVALUATED_FOR_DECLARED_SCOPE_NOT_CANONICALLY_ADMITTED",
  "canonical_G01_G24_status":"HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN",
  "canonical_promotion":"NOT_AUTHORIZED","operational_authorization":"NOT_GRANTED",
  "full_release_eligible":False,
  "protected_v25_exact_byte_comparison":"UNAVAILABLE_V25_BASELINE_NOT_PRESENT_IN_REPOSITORY",
  "formal_toolchain_and_HoTT_univalence":"NOT_PROVEN",
  "host_mTLS_or_remote_service_operations":"NOT_RUN_OUTSIDE_DECLARED_SCOPE",
  "offline_checkpoint_restore_test":"PASS_IN_G23_SELFTEST" if g23_scope_pass else "NOT_PROVEN",
  "exclusions":["canonical Louksna authority transfer or activation",
   "formal HoTT/univalence or complete model-to-implementation theorem",
   "production host/mTLS integration and remote-service rollback",
   "external regulatory or organizational certification"],
  "certification":"CERTIFIED_FOR_DECLARED_SCOPE" if certified else "NOT_GRANTED",
  "issued_at_utc":utc_now()}
 write(Path(a.out),payload);print(json.dumps(payload,indent=2,ensure_ascii=False))
 return 0

def main()->int:
 parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest="gate",required=True)
 q=sub.add_parser("g22");q.add_argument("--candidate-dir",required=True);q.add_argument("--candidate-sha",required=True)
 q.add_argument("--trusted-workflow-sha",required=True);q.add_argument("--candidate-source",required=True)
 q.add_argument("--trusted-source",required=True);q.add_argument("--out",required=True)
 q=sub.add_parser("g23");q.add_argument("--candidate-dir",required=True);q.add_argument("--candidate-sha",required=True)
 q.add_argument("--trusted-workflow-sha",required=True);q.add_argument("--validator-id",required=True)
 q.add_argument("--g22",required=True);q.add_argument("--out",required=True)
 q=sub.add_parser("g23-sign");q.add_argument("--candidate-dir",required=True);q.add_argument("--candidate-sha",required=True)
 q.add_argument("--trusted-workflow-sha",required=True);q.add_argument("--g22",required=True)
 q.add_argument("--g23-unsigned",required=True);q.add_argument("--out",required=True)
 q=sub.add_parser("g24");q.add_argument("--candidate-dir",required=True);q.add_argument("--candidate-sha",required=True)
  q.add_argument("--trusted-workflow-sha",required=True);q.add_argument("--g22",required=True)
  q.add_argument("--g23",required=True);q.add_argument("--g23-attestation-verification",required=True);q.add_argument("--out",required=True)
 a=parser.parse_args()
 try:return {"g22":g22,"g23":g23,"g23-sign":g23_sign,"g24":g24}[a.gate](a)
 except Exception as exc:
  value={"schema":"CUSTOSZV9_GATE_FAILURE/1.0","gate":a.gate,"status":"HOLD",
         "release_eligible":False,"certification":"NOT_GRANTED",
         "reason":type(exc).__name__+":"+str(exc)}
  write(Path(a.out),value);print(json.dumps(value,indent=2));return 2
if __name__=="__main__":raise SystemExit(main())
