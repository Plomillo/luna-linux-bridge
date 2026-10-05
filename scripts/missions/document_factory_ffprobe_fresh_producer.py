#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path

ACTIVE_SHA="43a82aa30607b8775c998fa39b2bc08bfc2a263f"
CANDIDATE_SHA="3774cb102ad6318fc824b2cb87c5055e9f5f4b0b"
CANDIDATE_REF="refs/heads/candidate/document-factory-v1-ffprobe-20261005"

def tele(phase,status,**kw):
    print("CUSTOSZ_FRESH_PRODUCER_TELEMETRY "+json.dumps({"at":datetime.now(timezone.utc).isoformat(),"phase":phase,"status":status,**kw},sort_keys=True),flush=True)

def run(cmd,cwd=None,timeout=240):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError("COMMAND_FAIL:"+repr(cmd)+"\n"+p.stdout[-5000:]+"\n"+p.stderr[-5000:])
    return p.stdout.strip()

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if len(sys.argv)!=4:
        raise SystemExit("USAGE: fresh_producer.py TARGET_ROOT OUT_DIR EXPECTED_SHA")
    target=Path(sys.argv[1]).resolve()
    outdir=Path(sys.argv[2]).resolve(); outdir.mkdir(parents=True,exist_ok=True)
    expected=sys.argv[3]
    if expected!=CANDIDATE_SHA: raise SystemExit("CANDIDATE_SHA_NOT_AUTHORIZED")

    tele("FRESH_PRODUCER_PRECHECK","RUNNING")
    if run(["git","-C",str(target),"rev-parse","HEAD"])!=ACTIVE_SHA:
        raise SystemExit("ACTIVE_TARGET_SHA_DRIFT")
    remote=run(["git","-C",str(target),"ls-remote","origin",CANDIDATE_REF])
    remote_sha=remote.split()[0] if remote else ""
    if remote_sha!=CANDIDATE_SHA: raise SystemExit("REMOTE_CANDIDATE_SHA_DRIFT:"+remote_sha)
    run(["git","-C",str(target),"fetch","--no-tags","origin",CANDIDATE_REF])
    if run(["git","-C",str(target),"rev-parse","FETCH_HEAD"])!=CANDIDATE_SHA:
        raise SystemExit("FETCHED_CANDIDATE_SHA_DRIFT")
    if run(["git","-C",str(target),"rev-parse",CANDIDATE_SHA+"^"])!=ACTIVE_SHA:
        raise SystemExit("CANDIDATE_PARENT_NOT_ACTIVE")
    tele("FRESH_PRODUCER_PRECHECK","PASS",candidate_sha=CANDIDATE_SHA,active_sha=ACTIVE_SHA)

    with tempfile.TemporaryDirectory(prefix="df-ffprobe-fresh-producer-") as td:
        root=Path(td)
        work=root/"candidate"
        frozen=root/"frozen"
        run(["git","-C",str(target),"worktree","add","--detach",str(work),CANDIDATE_SHA])
        try:
            tele("FRESH_PRODUCER_SCOPE","RUNNING")
            changed=run(["git","-C",str(work),"diff","--name-only",ACTIVE_SHA,CANDIDATE_SHA]).splitlines()
            bad=[x for x in changed if x and not x.startswith("document-factory/")]
            if bad: raise SystemExit("OUT_OF_SCOPE_PATHS:"+",".join(bad))
            tele("FRESH_PRODUCER_SCOPE","PASS",changed_paths=len(changed))

            tele("FRESH_PRODUCER_SELFTEST","RUNNING")
            selfout=run([sys.executable,"-B","document-factory/src/selftest.py"],cwd=work,timeout=240)
            selfobj=json.loads(selfout.splitlines()[-1])
            if selfobj.get("status")!="PASS" or selfobj.get("passed_count")!=13:
                raise SystemExit("CANONICAL_SELFTEST_NOT_13_PASS")
            tele("FRESH_PRODUCER_SELFTEST","PASS",passed_count=selfobj.get("passed_count"))

            tele("FRESH_PRODUCER_PROVIDER_SELFTEST","RUNNING")
            provider=run([sys.executable,"-B","document-factory/src/test_ffprobe_provider.py"],cwd=work,timeout=180)
            if "PASS" not in provider: raise SystemExit("PROVIDER_SELFTEST_NOT_PASS")
            tele("FRESH_PRODUCER_PROVIDER_SELFTEST","PASS")

            tele("FRESH_PRODUCER_PROFILE","RUNNING")
            run([sys.executable,"-B","document-factory/src/factory.py","validate-profile","document-factory/profiles/uniacc-neuroplasticidad-u2.json","--repo-root","."],cwd=work,timeout=240)
            tele("FRESH_PRODUCER_PROFILE","PASS")

            tele("FRESH_PRODUCER_FREEZE","RUNNING")
            frozen.mkdir(parents=True,exist_ok=True)
            framework=frozen/"framework"; framework.mkdir()
            src=work/"document-factory"
            for p in sorted(src.rglob("*")):
                rel=p.relative_to(src)
                dst=framework/rel
                if p.is_dir(): dst.mkdir(parents=True,exist_ok=True)
                elif p.is_file():
                    dst.parent.mkdir(parents=True,exist_ok=True)
                    dst.write_bytes(p.read_bytes())
            rows=[]
            for f in sorted(x for x in frozen.rglob("*") if x.is_file()):
                rows.append({"path":f.relative_to(frozen).as_posix(),"sha256":sha(f),"size_bytes":f.stat().st_size})
            digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            producer={
              "schema":"DOCUMENT_FACTORY_FFPROBE_FRESH_PRODUCER/1.0",
              "status":"PASS_FRESH_PRODUCER_PENDING_INDEPENDENT_G23_G24",
              "candidate_head_sha":CANDIDATE_SHA,
              "active_anchor_sha":ACTIVE_SHA,
              "candidate_parent_is_active":True,
              "changed_paths":changed,
              "selftest":selfobj,
              "provider_selftest":"PASS",
              "profile_validation":"PASS",
              "candidate_digest_sha256":digest,
              "file_count":len(rows),
              "g23":"NOT_EXECUTED",
              "g24":"NOT_EXECUTED",
              "certification_authority":False,
              "certification_propagation":False,
              "next_state":"INDEPENDENT_PRODUCER_G23_G24_REQUIRED",
              "produced_at_utc":datetime.now(timezone.utc).isoformat()
            }
            (frozen/"CANDIDATE_DIGEST.txt").write_text(digest+"\n",encoding="utf-8")
            (frozen/"FROZEN_CANDIDATE.json").write_text(json.dumps({
              "schema":"DOCUMENT_FACTORY_FROZEN_CANDIDATE/1.0",
              "frozen":True,
              "candidate_head_sha":CANDIDATE_SHA,
              "candidate_digest_sha256":digest,
              "files":rows,
              "g23":"NOT_EXECUTED",
              "g24":"NOT_EXECUTED"
            },indent=2,sort_keys=True)+"\n",encoding="utf-8")
            (outdir/"FRESH_PRODUCER.json").write_text(json.dumps(producer,indent=2,sort_keys=True)+"\n",encoding="utf-8")
            trace=target/"document-factory/custosz/FRESH_PRODUCER_CONTINUATION.json"
            trace.parent.mkdir(parents=True,exist_ok=True)
            trace.write_text(json.dumps(producer,indent=2,sort_keys=True)+"\n",encoding="utf-8")
            tele("FRESH_PRODUCER_FREEZE","PASS",candidate_digest_sha256=digest,file_count=len(rows))
            tele("FRESH_PRODUCER","PASS",next_state=producer["next_state"])
        finally:
            run(["git","-C",str(target),"worktree","remove","--force",str(work)],timeout=60)

if __name__=="__main__":
    main()
