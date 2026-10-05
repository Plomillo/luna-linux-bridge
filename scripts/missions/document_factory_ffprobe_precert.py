#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path

ACTIVE_SHA="43a82aa30607b8775c998fa39b2bc08bfc2a263f"
CANDIDATE_SHA="3774cb102ad6318fc824b2cb87c5055e9f5f4b0b"
CANDIDATE_REF="refs/heads/candidate/document-factory-v1-ffprobe-20261005"

def tele(phase,status,**kw):
    print("CUSTOSZ_PRECERT_TELEMETRY "+json.dumps({"at":datetime.now(timezone.utc).isoformat(),"phase":phase,"status":status,**kw},sort_keys=True),flush=True)

def run(cmd,cwd=None,timeout=180):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError("COMMAND_FAIL:"+repr(cmd)+"\n"+p.stdout[-4000:]+"\n"+p.stderr[-4000:])
    return p.stdout.strip()

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if len(sys.argv)!=4:
        raise SystemExit("USAGE: precert.py TARGET_ROOT OUT_DIR EXPECTED_SHA")
    target=Path(sys.argv[1]).resolve()
    outdir=Path(sys.argv[2]).resolve(); outdir.mkdir(parents=True,exist_ok=True)
    expected=sys.argv[3]
    if expected!=CANDIDATE_SHA: raise SystemExit("CANDIDATE_SHA_NOT_AUTHORIZED")

    tele("PRECHECK","RUNNING")
    if run(["git","-C",str(target),"rev-parse","HEAD"])!=ACTIVE_SHA:
        raise SystemExit("ACTIVE_TARGET_SHA_DRIFT")
    remote=run(["git","-C",str(target),"ls-remote","origin",CANDIDATE_REF])
    remote_sha=remote.split()[0] if remote else ""
    if remote_sha!=CANDIDATE_SHA:
        raise SystemExit("REMOTE_CANDIDATE_SHA_DRIFT:"+remote_sha)
    run(["git","-C",str(target),"fetch","--no-tags","origin",CANDIDATE_REF])
    if run(["git","-C",str(target),"rev-parse","FETCH_HEAD"])!=CANDIDATE_SHA:
        raise SystemExit("FETCHED_CANDIDATE_SHA_DRIFT")
    parent=run(["git","-C",str(target),"rev-parse",CANDIDATE_SHA+"^"])
    if parent!=ACTIVE_SHA: raise SystemExit("CANDIDATE_PARENT_NOT_ACTIVE")
    tele("PRECHECK","PASS",candidate_sha=CANDIDATE_SHA,active_sha=ACTIVE_SHA)

    with tempfile.TemporaryDirectory(prefix="df-ffprobe-precert-") as td:
        work=Path(td)/"candidate"
        run(["git","-C",str(target),"worktree","add","--detach",str(work),CANDIDATE_SHA])
        try:
            tele("SCOPE_VALIDATION","RUNNING")
            changed=run(["git","-C",str(work),"diff","--name-only",ACTIVE_SHA,CANDIDATE_SHA]).splitlines()
            bad=[x for x in changed if x and not x.startswith("document-factory/")]
            if bad: raise SystemExit("OUT_OF_SCOPE_PATHS:"+",".join(bad))
            tele("SCOPE_VALIDATION","PASS",changed_paths=len(changed))

            prov=json.loads((work/"document-factory/providers/ffprobe/linux-amd64/PROVENANCE.json").read_text())
            state=json.loads((work/"document-factory/custosz/CURRENT_STATE.json").read_text())
            tele("PROVENANCE_REVALIDATION","RUNNING")
            if prov.get("status")!="PASS": raise SystemExit("PROVENANCE_NOT_PASS")
            if prov.get("upstream",{}).get("pgp_signature_verified") is not True: raise SystemExit("PGP_NOT_VERIFIED")
            if prov.get("final_provider_selftest")!="FFPROBE_PROVIDER_ADMISSION_SELFTEST=PASS": raise SystemExit("PROVIDER_SELFTEST_EVIDENCE_INVALID")
            if state.get("ffprobe_provider_candidate",{}).get("status")!="PASS_PENDING_FRESH_G23_G24": raise SystemExit("CANDIDATE_STATE_INVALID")
            if state.get("g23")!="NOT_PROPAGATED" or state.get("g24")!="NOT_PROPAGATED": raise SystemExit("CERTIFICATION_PROPAGATION_INVALID")
            tele("PROVENANCE_REVALIDATION","PASS",ffprobe_sha256=prov["binary"]["sha256"])

            tele("PROVIDER_SELFTEST","RUNNING")
            provider=run([sys.executable,"-B","document-factory/src/test_ffprobe_provider.py"],cwd=work,timeout=120)
            if "PASS" not in provider: raise SystemExit("PROVIDER_SELFTEST_NOT_PASS")
            tele("PROVIDER_SELFTEST","PASS")

            tele("CANONICAL_SELFTEST","RUNNING")
            selfout=run([sys.executable,"-B","document-factory/src/selftest.py"],cwd=work,timeout=180)
            selfobj=json.loads(selfout.splitlines()[-1])
            if selfobj.get("status")!="PASS" or "FFPROBE_PROVIDER_ADMISSION" not in set(selfobj.get("tests") or []):
                raise SystemExit("CANONICAL_SELFTEST_NOT_PASS")
            tele("CANONICAL_SELFTEST","PASS",passed_count=selfobj.get("passed_count"))

            tele("PROFILE_VALIDATION","RUNNING")
            run([sys.executable,"-B","document-factory/src/factory.py","validate-profile","document-factory/profiles/uniacc-neuroplasticidad-u2.json","--repo-root","."],cwd=work,timeout=180)
            tele("PROFILE_VALIDATION","PASS")

            tele("CANDIDATE_DIGEST_LEDGER","RUNNING")
            rows=[]
            for f in sorted(x for x in (work/"document-factory").rglob("*") if x.is_file()):
                rows.append({"path":f.relative_to(work).as_posix(),"sha256":sha(f),"size_bytes":f.stat().st_size})
            digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            tele("CANDIDATE_DIGEST_LEDGER","PASS",file_count=len(rows),content_digest_sha256=digest)

            evidence={
              "schema":"DOCUMENT_FACTORY_FFPROBE_PRECERT_CONTINUATION/1.0",
              "status":"PASS_PRECERT_NOT_G23_G24",
              "worker":"CUSTOSZ_V7",
              "runtime":"CUSTOSZ_RUNTIME_V1",
              "candidate_head_sha":CANDIDATE_SHA,
              "active_anchor_sha":ACTIVE_SHA,
              "candidate_parent_is_active":True,
              "candidate_remote_unchanged":True,
              "changed_paths":changed,
              "provider_selftest":"PASS",
              "canonical_selftest":selfobj,
              "profile_validation":"PASS",
              "candidate_content_digest_sha256":digest,
              "candidate_file_count":len(rows),
              "pgp_signature_verified":True,
              "g23":"NOT_EXECUTED_BY_PRECERT",
              "g24":"NOT_EXECUTED_BY_PRECERT",
              "certification_authority":False,
              "active_authorized":False,
              "certification_propagation":False,
              "next_state":"FRESH_PRODUCER_INDEPENDENT_G23_G24_REQUIRED",
              "observed_at_utc":datetime.now(timezone.utc).isoformat()
            }
            ep=outdir/"PRECERT_CONTINUATION.json"
            ep.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
            trace=target/"document-factory/custosz/PRECERT_CONTINUATION.json"
            trace.parent.mkdir(parents=True,exist_ok=True)
            trace.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
            tele("PRECERT_CONTINUATION","PASS",next_state=evidence["next_state"])
        finally:
            run(["git","-C",str(target),"worktree","remove","--force",str(work)],timeout=60)

if __name__=="__main__":
    main()
