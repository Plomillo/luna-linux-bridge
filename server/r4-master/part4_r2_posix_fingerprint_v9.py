#!/usr/bin/env python3
import argparse,hashlib,json,os,pathlib,stat,time

def typ(mode):
    if stat.S_ISREG(mode): return "file"
    if stat.S_ISDIR(mode): return "dir"
    if stat.S_ISLNK(mode): return "symlink"
    return "other"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--allow-root-empty-ext4-lostfound",action="store_true")
    ap.add_argument("--expect")
    a=ap.parse_args()
    root=pathlib.Path(a.root)
    out=pathlib.Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256(); count=0; counts={"file":0,"dir":0,"symlink":0,"other":0}
    technical=None
    stack=[root]
    while stack:
        d=stack.pop()
        entries=sorted(os.scandir(d),key=lambda e:e.name,reverse=True)
        dirs=[]
        for e in entries:
            p=pathlib.Path(e.path); rel=p.relative_to(root).as_posix()
            if rel=="lost+found" and d==root and a.allow_root_empty_ext4_lostfound:
                st=e.stat(follow_symlinks=False)
                if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode) or os.path.ismount(pathlib.Path(e.path)):
                    raise SystemExit("HOLD:UNSAFE_ROOT_LOSTFOUND_TYPE_OR_MOUNT")
                try: children=list(os.scandir(pathlib.Path(e.path)))
                except OSError as ex: raise SystemExit("HOLD:LOSTFOUND_SCAN:"+repr(ex))
                ok=(stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode)
                    and st.st_uid==0 and st.st_gid==0 and stat.S_IMODE(st.st_mode)==0o700
                    and st.st_dev==root.stat().st_dev and os.path.ismount(root)
                    and not os.path.ismount(pathlib.Path(e.path)) and not children)
                if not ok: raise SystemExit("HOLD:INVALID_ROOT_LOSTFOUND")
                technical={"path":rel,"owner":st.st_uid,"group":st.st_gid,
                           "mode":oct(stat.S_IMODE(st.st_mode)),"empty":True}
                continue
            st=e.stat(follow_symlinks=False); t=typ(st.st_mode); counts[t]+=1; count+=1
            rec=[rel,t,str(st.st_uid),str(st.st_gid),oct(stat.S_IMODE(st.st_mode)),"DIR" if t=="dir" else str(st.st_nlink),str(st.st_rdev)]
            h.update(("\0".join(rec)+"\n").encode("utf-8","surrogateescape"))
            if t=="dir": dirs.append(p)
        stack.extend(dirs)
    result={"schema":"LOUKSNA_R4_PART4_R2_POSIX_FINGERPRINT_V9/1.0","root":str(root),"root_technical_exclusion":technical,"records":count,
            "counts":counts,"fingerprint_sha256":h.hexdigest(),"directory_nlink_normalized":True,"status":"PASS",
            "started_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    if a.allow_root_empty_ext4_lostfound and technical is None: result["status"]="HOLD"
    if a.expect:
        exp=json.loads(pathlib.Path(a.expect).read_text())
        same=(result["records"]==exp.get("records") and result["counts"]==exp.get("counts") and result["fingerprint_sha256"]==exp.get("fingerprint_sha256"))
        result["matches_expected"]=same
        result["expected_fingerprint_sha256"]=exp.get("fingerprint_sha256")
        if not same: result["status"]="HOLD"
    result["finished_at_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result["status"]=="PASS" else 3
if __name__=="__main__": raise SystemExit(main())
