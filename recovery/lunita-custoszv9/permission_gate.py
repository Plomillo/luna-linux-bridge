#!/usr/bin/env python3
"""Fail-closed permission gate. Default is read-only; no network/download code."""
import argparse, datetime, hashlib, json, os, pathlib, pwd, shutil, stat, subprocess, sys

CID = "G06_REBUILD_CANDIDATE_R1"
SCHEMAS = {
    "state.json": "CUSTOSZ_G06_REBUILD_CANDIDATE_STATE/1.0",
    "BUILD_PLAN.json": "CUSTOSZ_G06_REBUILD_CANDIDATE_PLAN/1.0",
    "BASE_REBUILD_RECEIPT.json": "CUSTOSZ_G06_REBUILD_STAGE_RECEIPT/1.0",
}
class GateError(RuntimeError): pass

def digest(p):
    h = hashlib.sha256()
    with pathlib.Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def snap(p):
    s = pathlib.Path(p).stat()
    return {"path": str(p), "uid": s.st_uid, "gid": s.st_gid,
            "mode": format(stat.S_IMODE(s.st_mode), "04o"),
            "bytes": s.st_size, "sha256": digest(p)}

def read_json(p):
    p = pathlib.Path(p)
    try: obj = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise GateError("FILE_MISSING:"+p.name) from e
    except PermissionError as e: raise GateError("ACCESS_DENIED:"+p.name) from e
    except (OSError, ValueError) as e: raise GateError("INVALID_JSON_OR_IO:"+p.name) from e
    if not isinstance(obj, dict): raise GateError("JSON_ROOT_NOT_OBJECT:"+p.name)
    return obj

def inspect(candidate, user):
    account = pwd.getpwnam(user)
    paths = {n: pathlib.Path(candidate)/n for n in SCHEMAS}
    objects = {n: read_json(p) for n,p in paths.items()}
    for n,obj in objects.items():
        if obj.get("candidate_id") != CID: raise GateError("IDENTITY_MISMATCH:"+n)
        if obj.get("schema") != SCHEMAS[n]: raise GateError("SCHEMA_MISMATCH:"+n)
    current = {n:snap(p) for n,p in paths.items()}
    expected = {
        "state.json": (account.pw_uid, "0600"),
        "BUILD_PLAN.json": (account.pw_uid, "0400"),
        "BASE_REBUILD_RECEIPT.json": (account.pw_uid, "0640"),
    }
    policy = {n: current[n]["uid"] == u and current[n]["mode"] == m
              for n,(u,m) in expected.items()}
    return {"schema":"CUSTOSZ_LUNITA_PERMISSION_GATE/1.0",
            "observed_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "candidate_id":CID,"service_user":user,"service_uid":account.pw_uid,
            "current":current,"expected":expected,"policy_match":policy,
            "all_policy_match":all(policy.values()),"phase":objects["state"].get("phase"),
            "certification":"NOT_GRANTED","network_or_download":False}

def service_probe(candidate, user):
    code = r'''import os,json,pathlib,tempfile
c=pathlib.Path(os.environ["CAND"])
json.loads((c/"state.json").read_text()); json.loads((c/"BUILD_PLAN.json").read_text())
try: (c/"BUILD_PLAN.json").open("r+").close()
except PermissionError: pass
else: raise SystemExit("FAIL_PLAN_WRITE_ALLOWED")
fd,n=tempfile.mkstemp(dir=c,prefix=".custosz-probe-"); os.write(fd,b"x"); os.close(fd); os.unlink(n)
print("PASS_STATE_READ;PASS_PLAN_READ;PASS_PLAN_WRITE_DENIED;PASS_STATE_DIR_WRITE")'''
    env=os.environ.copy(); env["CAND"]=str(candidate)
    try: p=subprocess.run(["runuser","-u",user,"--",sys.executable,"-c",code],
                          env=env,text=True,capture_output=True,timeout=20)
    except (OSError,subprocess.TimeoutExpired) as e:
        return {"status":"BLOCKED","error":type(e).__name__+":"+str(e)}
    return {"status":"PASS" if p.returncode==0 else "FAIL","rc":p.returncode,
            "stdout":p.stdout.strip(),"stderr":p.stderr.strip()}

def apply(candidate, root, user):
    if os.geteuid()!=0: raise GateError("ROOT_REQUIRED")
    account=pwd.getpwnam(user)
    current=inspect(candidate,user)
    paths={n:pathlib.Path(candidate)/n for n in SCHEMAS}
    before={n:snap(p) for n,p in paths.items()}
    ck=pathlib.Path(root)/"state/checkpoints"/(
        "LUNITA_V9_PERMISSION_GATE_"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ck.mkdir(parents=True,mode=0o700)
    for p in paths.values():
        target=ck/p.name; shutil.copy2(p,target)
        os.chown(target,account.pw_uid,account.pw_gid); os.chmod(target,0o600)
    os.chown(ck,account.pw_uid,account.pw_gid); os.chmod(ck,0o700)
    meta={"schema":"CUSTOSZ_PERMISSION_CHECKPOINT/1.0","candidate_id":CID,
          "checkpoint":str(ck),"before":before,
          "rollback":"Restore bytes and recorded uid/gid/mode. Never replace frozen G06/G08."}
    m=ck/"CHECKPOINT.json"; m.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    os.chown(m,account.pw_uid,account.pw_gid); os.chmod(m,0o600)
    os.chown(paths["state.json"],account.pw_uid,account.pw_gid); os.chmod(paths["state.json"],0o600)
    os.chown(paths["BUILD_PLAN.json"],account.pw_uid,account.pw_gid); os.chmod(paths["BUILD_PLAN.json"],0o400)
    after={n:snap(p) for n,p in paths.items()}
    for n in paths:
        if before[n]["sha256"] != after[n]["sha256"]: raise GateError("HASH_CHANGED:"+n)
    if before["BASE_REBUILD_RECEIPT.json"] != after["BASE_REBUILD_RECEIPT.json"]:
        raise GateError("RECEIPT_CHANGED")
    final=inspect(candidate,user)
    final.update({"operation":"APPLY_ONLY_STATE_AND_PLAN_PERMISSIONS",
                  "checkpoint":str(ck),"before":before,"after":after,
                  "content_hashes_preserved":True,"service_probe":service_probe(candidate,user)})
    final["result"]="PASS" if final["all_policy_match"] and final["service_probe"]["status"]=="PASS" else "FAIL"
    return final

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--custosz-root",required=True)
    a.add_argument("--service-user",default="diegoignacionorambuenamiranda")
    a.add_argument("--apply",action="store_true",help="checkpoint and apply two approved metadata changes")
    a.add_argument("--report")
    x=a.parse_args()
    root=pathlib.Path(x.custosz_root).resolve()
    c=root/"state/g06_rebuild_candidates"/CID
    try:
        out=apply(c,root,x.service_user) if x.apply else inspect(c,x.service_user)
        if x.apply and not out.get("service_probe"): out["service_probe"]=service_probe(c,x.service_user)
        if x.report:
            d=pathlib.Path(x.report); t=d.with_name(d.name+".tmp")
            t.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); os.replace(t,d)
        print(json.dumps(out,indent=2,sort_keys=True))
        ok=out.get("result")=="PASS" if x.apply else out["all_policy_match"]
        return 0 if ok else 2
    except (GateError, OSError, KeyError, ValueError) as e:
        print(json.dumps({"result":"BLOCKED","error":type(e).__name__+":"+str(e),
                          "certification":"NOT_GRANTED","network_or_download":False}),file=sys.stderr)
        return 2
if __name__=="__main__": raise SystemExit(main())
