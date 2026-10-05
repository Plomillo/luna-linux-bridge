#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys,tarfile,tempfile,time
from pathlib import Path
from datetime import datetime,timezone

ACTIVE_SHA="43a82aa30607b8775c998fa39b2bc08bfc2a263f"
ACTIVE_DIGEST="b0c59f37c70e58ca42f7fd215fad890e9a24b255d369110665e7141f26f57404"
VERSION="9.0.2"
SOURCE_URL="https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz"
SIG_URL="https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz.asc"
KEY_URL="https://ffmpeg.org/ffmpeg-devel.asc"
KEY_FPR="FCF986EA15E6E293A5644F10B4322F04D67658D8"

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def tele(phase,status="RUNNING",**kw):
    print("CUSTOSZ_FFPROBE_TELEMETRY "+json.dumps({"at":utc(),"phase":phase,"status":status,**kw},sort_keys=True),flush=True)
def run(cmd,cwd=None,timeout=120,env=None):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout,env=env)
    if p.returncode:
        raise RuntimeError("COMMAND_FAIL:"+repr(cmd)+"\nSTDOUT:\n"+p.stdout[-6000:]+"\nSTDERR:\n"+p.stderr[-6000:])
    return p.stdout.strip()
def jload(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def jwrite(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def main():
    if len(sys.argv)!=5: raise SystemExit("usage: materializer TARGET_ROOT MAIN_ROOT MAILBOX_ROOT OUT_DIR")
    target,main_root,mailbox,outdir=map(lambda x:Path(x).resolve(),sys.argv[1:5])
    outdir.mkdir(parents=True,exist_ok=True)
    tele("PRECHECK")
    head=run(["git","-C",str(target),"rev-parse","HEAD"])
    if head!=ACTIVE_SHA: raise SystemExit("ACTIVE_SHA_DRIFT:"+head)
    ledger=jload(main_root/"operational-authorizations/document-factory/CURRENT.json")
    if not (ledger.get("status")=="PASS" and ledger.get("active_authorized") is True and ledger.get("candidate_head_sha")==ACTIVE_SHA and ledger.get("candidate_digest_sha256")==ACTIVE_DIGEST):
        raise SystemExit("ACTIVE_LEDGER_MISMATCH")
    if ledger.get("certification_propagation") is not False: raise SystemExit("CERTIFICATION_PROPAGATION_CONTROL_BROKEN")
    tele("PRECHECK","PASS",active_sha=ACTIVE_SHA,active_digest=ACTIVE_DIGEST)

    for exe in ("curl","gpg","make","cc"):
        if not shutil.which(exe): raise SystemExit("REQUIRED_BUILD_TOOL_MISSING:"+exe)

    with tempfile.TemporaryDirectory(prefix="custosz-ffprobe-") as td:
        work=Path(td)
        tar=work/f"ffmpeg-{VERSION}.tar.xz"; sig=work/(tar.name+".asc"); key=work/"ffmpeg-devel.asc"
        tele("FETCH_OFFICIAL_RELEASE")
        run(["curl","-fL","--retry","2","--connect-timeout","15",SOURCE_URL,"-o",str(tar)],timeout=300)
        run(["curl","-fL","--retry","2","--connect-timeout","15",SIG_URL,"-o",str(sig)],timeout=120)
        run(["curl","-fL","--retry","2","--connect-timeout","15",KEY_URL,"-o",str(key)],timeout=120)
        tele("FETCH_OFFICIAL_RELEASE","PASS",source_bytes=tar.stat().st_size)

        gnupg=work/"gnupg"; gnupg.mkdir(mode=0o700)
        env=dict(os.environ); env["GNUPGHOME"]=str(gnupg)
        run(["gpg","--batch","--import",str(key)],timeout=30,env=env)
        fprs=run(["gpg","--batch","--with-colons","--fingerprint"],timeout=30,env=env)
        observed=[line.split(":")[9] for line in fprs.splitlines() if line.startswith("fpr:")]
        if KEY_FPR not in observed: raise SystemExit("FFMPEG_SIGNING_KEY_FINGERPRINT_MISMATCH")
        tele("VERIFY_PGP_FINGERPRINT","PASS",fingerprint=KEY_FPR)
        verify=run(["gpg","--batch","--status-fd","1","--verify",str(sig),str(tar)],timeout=60,env=env)
        if ("VALIDSIG "+KEY_FPR) not in verify: raise SystemExit("FFMPEG_RELEASE_SIGNATURE_NOT_VALID")
        source_sha=sha(tar)
        tele("VERIFY_PGP_SIGNATURE","PASS",source_sha256=source_sha)

        with tarfile.open(tar,"r:xz") as tf: tf.extractall(work)
        src=work/f"ffmpeg-{VERSION}"
        if not src.is_dir(): raise SystemExit("SOURCE_EXTRACT_FAIL")
        prefix=work/"install"
        configure=[
          "./configure",
          "--prefix="+str(prefix),
          "--disable-ffplay",
          "--disable-doc",
          "--disable-debug",
          "--disable-network",
          "--disable-autodetect",
          "--enable-ffprobe",
          "--enable-ffmpeg"
        ]
        tele("CONFIGURE_BUILD")
        run(configure,cwd=src,timeout=300)
        tele("BUILD_FFPROBE",status="RUNNING",jobs=2)
        run(["make","-j2","ffprobe","ffmpeg"],cwd=src,timeout=1800)
        ffprobe=src/"ffprobe"; ffmpeg=src/"ffmpeg"
        if not ffprobe.is_file() or not ffmpeg.is_file(): raise SystemExit("BUILD_OUTPUT_MISSING")
        if shutil.which("strip"):
            run(["strip",str(ffprobe)],timeout=60)
        binary_sha=sha(ffprobe)
        version_line=run([str(ffprobe),"-version"],timeout=30).splitlines()[0]
        if "ffprobe version "+VERSION not in version_line: raise SystemExit("FFPROBE_VERSION_MISMATCH:"+version_line)
        tele("BUILD_FFPROBE","PASS",binary_sha256=binary_sha,version_line=version_line)

        sample=work/"synthetic.mkv"
        run([str(ffmpeg),"-v","error","-f","lavfi","-i","testsrc=size=640x360:rate=25","-t","1","-c:v","ffv1","-y",str(sample)],timeout=120)
        probe_text=run([str(ffprobe),"-v","error","-show_entries","stream=codec_type,width,height","-show_entries","format=duration","-of","json",str(sample)],timeout=60)
        probe=json.loads(probe_text)
        video=next((x for x in probe.get("streams",[]) if x.get("codec_type")=="video"),None)
        duration=float((probe.get("format") or {}).get("duration") or 0)
        if not video or int(video.get("width",0))!=640 or int(video.get("height",0))!=360 or not (0.9<=duration<=1.1):
            raise SystemExit("FFPROBE_SYNTHETIC_MEDIA_TEST_FAIL:"+probe_text)
        tele("FUNCTIONAL_TEST_SYNTHETIC_MEDIA","PASS",width=640,height=360,duration=duration)

        tele("BASELINE_NON_REGRESSION")
        baseline=run([sys.executable,"-B","document-factory/src/selftest.py"],cwd=target,timeout=180)
        completion=run([sys.executable,"-B","document-factory/src/test_completion.py"],cwd=target,timeout=180)
        e2e=run([sys.executable,"-B","document-factory/src/synthetic_e2e.py"],cwd=target,timeout=180)
        tele("BASELINE_NON_REGRESSION","PASS")

        provider_dir=target/"document-factory/providers/ffprobe/linux-amd64"
        provider_dir.mkdir(parents=True,exist_ok=True)
        binary=provider_dir/"ffprobe"
        shutil.copy2(ffprobe,binary); binary.chmod(0o755)
        if sha(binary)!=binary_sha: raise SystemExit("PERSISTED_BINARY_HASH_MISMATCH")
        ldd=run(["ldd",str(binary)],timeout=30) if shutil.which("ldd") else "LDD_UNAVAILABLE"

        lock_path=target/"document-factory/toolchain.lock.json"
        lock=jload(lock_path)
        row=next((x for x in lock.get("providers",[]) if x.get("id")=="ffprobe"),None)
        if row is None: raise SystemExit("FFPROBE_LOCK_ROW_MISSING")
        row.clear(); row.update({
          "id":"ffprobe",
          "version":VERSION,
          "source":SOURCE_URL,
          "source_signature":SIG_URL,
          "signing_key":KEY_URL,
          "signing_key_fingerprint":KEY_FPR,
          "sha256":source_sha,
          "binary_path":"document-factory/providers/ffprobe/linux-amd64/ffprobe",
          "binary_sha256":binary_sha,
          "architecture":"linux-amd64",
          "build":{"configure":configure[1:],"make_jobs":2,"external_autodetect":False,"network":False},
          "state":"PGP_VERIFIED_BUILT_FUNCTIONALLY_TESTED_CANDIDATE_PENDING_FRESH_G23_G24",
          "required_for":["video_validation"],
          "certification_inherited":False
        })
        jwrite(lock_path,lock)

        media_path=target/"document-factory/src/media_validation.py"
        media=media_path.read_text(encoding="utf-8")
        if "def ffprobe_runtime_admission(" not in media:
            media += r'''

def ffprobe_runtime_admission(lock,repo_root):
    import hashlib,subprocess
    from pathlib import Path
    obj=_load(lock)
    row=next((x for x in obj.get("providers",[]) if x.get("id")=="ffprobe"),None)
    failures=[]
    if not row:
        return {"status":"FAIL","admitted":False,"failures":["FFPROBE_NOT_DECLARED"]}
    for key in ("version","source","source_signature","signing_key_fingerprint","sha256","binary_path","binary_sha256"):
        if not row.get(key): failures.append("FFPROBE_LOCK_FIELD_MISSING:"+key)
    p=Path(repo_root)/str(row.get("binary_path",""))
    if not p.is_file(): failures.append("FFPROBE_BINARY_MISSING")
    else:
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        if h!=row.get("binary_sha256"): failures.append("FFPROBE_BINARY_HASH_MISMATCH")
        q=subprocess.run([str(p),"-version"],text=True,capture_output=True,timeout=10)
        if q.returncode!=0 or ("ffprobe version "+str(row.get("version"))) not in q.stdout:
            failures.append("FFPROBE_BINARY_VERSION_MISMATCH")
    if row.get("certification_inherited") is not False:
        failures.append("CERTIFICATION_INHERITANCE_FORBIDDEN")
    return {"status":"PASS" if not failures else "FAIL","admitted":not failures,"failures":failures,"provider":row.get("id"),"version":row.get("version"),"binary_path":row.get("binary_path"),"binary_sha256":row.get("binary_sha256"),"certification_state":"CANDIDATE_PENDING_FRESH_G23_G24"}
'''
            media_path.write_text(media,encoding="utf-8")

        provider_test=target/"document-factory/src/test_ffprobe_provider.py"
        provider_test.write_text("""#!/usr/bin/env python3
import pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from media_validation import ffprobe_runtime_admission
r=ffprobe_runtime_admission(ROOT/"toolchain.lock.json",ROOT.parent)
assert r["status"]=="PASS", r
assert r["admitted"] is True
assert r["certification_state"]=="CANDIDATE_PENDING_FRESH_G23_G24"
print("FFPROBE_PROVIDER_ADMISSION_SELFTEST=PASS")
""",encoding="utf-8")
        provider_test.chmod(0o755)
        provider_selftest=run([sys.executable,"-B","document-factory/src/test_ffprobe_provider.py"],cwd=target,timeout=60)

        claims_path=target/"document-factory/CLAIMS.json"; claims=jload(claims_path)
        if not any(x.get("claim_id")=="DF-CLM-013" for x in claims.get("claims",[])):
            claims["claims"].append({"claim_id":"DF-CLM-013","property":"FFprobe 9.0.2 provider provenance is PGP-verified, binary-hash-pinned and functionally tested for profile-driven audiovisual metadata inspection.","acceptance":"Official FFmpeg release signature verifies against pinned fingerprint; source and binary SHA-256 are recorded; synthetic media probe and provider selftest pass; fresh G23/G24 required."})
        old="Audiovisual validation until FFprobe provider is pinned and admitted."
        if old in claims.get("excluded_claims",[]): claims["excluded_claims"].remove(old)
        new="Semantic or disciplinary assessment of audiovisual content beyond mechanically observable media metadata."
        if new not in claims.get("excluded_claims",[]): claims["excluded_claims"].append(new)
        jwrite(claims_path,claims)

        evidence={
          "schema":"DOCUMENT_FACTORY_FFPROBE_PROVIDER_EVIDENCE/1.0",
          "status":"PASS",
          "worker":"CUSTOSZ_V7",
          "runtime":"CUSTOSZ_RUNTIME_V1",
          "active_certified_anchor":{"candidate_head_sha":ACTIVE_SHA,"candidate_digest_sha256":ACTIVE_DIGEST,"preserved":True},
          "upstream":{"name":"FFmpeg","version":VERSION,"source":SOURCE_URL,"signature":SIG_URL,"key":KEY_URL,"signing_key_fingerprint":KEY_FPR,"pgp_signature_verified":True,"source_sha256":source_sha},
          "binary":{"path":"document-factory/providers/ffprobe/linux-amd64/ffprobe","sha256":binary_sha,"version_line":version_line,"ldd":ldd},
          "synthetic_probe":{"status":"PASS","probe":probe},
          "baseline_selftest":baseline,
          "completion_selftest":completion,
          "synthetic_e2e":e2e,
          "provider_selftest":provider_selftest,
          "certification_inherited":False,
          "g23":"NOT_EXECUTED_FOR_CHANGE",
          "g24":"NOT_EXECUTED_FOR_CHANGE",
          "observed_at_utc":utc()
        }
        jwrite(provider_dir/"PROVENANCE.json",evidence)

        state_path=target/"document-factory/custosz/CURRENT_STATE.json"; state=jload(state_path)
        state.update({
          "schema":"DOCUMENT_FACTORY_CUSTOSZ_WORK_STATE/3.0",
          "worker":"CUSTOSZ_V7",
          "runtime":"CUSTOSZ_RUNTIME_V1",
          "active_certified_anchor_sha":ACTIVE_SHA,
          "active_certified_anchor_digest_sha256":ACTIVE_DIGEST,
          "active_certification_preserved":True,
          "material_step":"FFPROBE_PROVIDER_PGP_VERIFIED_BUILT_TESTED",
          "ffprobe_provider_candidate":{"status":"PASS_PENDING_FRESH_G23_G24","version":VERSION,"source_sha256":source_sha,"binary_sha256":binary_sha,"signing_key_fingerprint":KEY_FPR},
          "g23":"NOT_PROPAGATED",
          "g24":"NOT_PROPAGATED",
          "next_work":["FRESH_PRODUCER_VALIDATION_FOR_FFPROBE_CHANGE","INDEPENDENT_VALIDATION","G23","G24","NEW_OPERATIONAL_AUTHORIZATION"]
        })
        scopes=[x for x in state.get("scope_exclusions",[]) if x!="FFPROBE_RUNTIME_CLAIM_UNTIL_PROVIDER_PROVENANCE_PINNED"]
        scopes.append("FFPROBE_CHANGE_NOT_IN_ACTIVE_CERTIFIED_SCOPE_UNTIL_FRESH_G23_G24")
        state["scope_exclusions"]=sorted(set(scopes))
        jwrite(state_path,state)

        report={
          "schema":"CUSTOSZ_FFPROBE_ADMISSION_RESULT/1.0",
          "status":"PASS",
          "active_certification_preserved":True,
          "active_sha":ACTIVE_SHA,
          "active_digest":ACTIVE_DIGEST,
          "ffprobe_version":VERSION,
          "source_sha256":source_sha,
          "binary_sha256":binary_sha,
          "signature_fingerprint":KEY_FPR,
          "functional_test":"PASS",
          "non_regression":"PASS",
          "certification_inherited":False,
          "next_state":"FFPROBE_PROVIDER_CANDIDATE_READY_FOR_FRESH_PRODUCER_VALIDATION"
        }
        jwrite(outdir/"RESULT.json",report)
        tele("MATERIAL_CANDIDATE_READY","PASS",source_sha256=source_sha,binary_sha256=binary_sha,next_state=report["next_state"])
if __name__=="__main__": main()
