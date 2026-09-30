#!/usr/bin/env python3
import argparse,gzip,hashlib,json,os,pathlib,stat,time

EXPECTED_MANIFEST_SHA256="99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e"
EXPECTED_COUNTS={"file":436072,"dir":62016,"symlink":4,"other":0}
EXPECTED_BYTES=200490852057
EXPECTED_RECORDS=498092

def sha256_file(path,chunk=8*1024*1024):
    h=hashlib.sha256()
    with open(path,"rb",buffering=0) as f:
        for b in iter(lambda:f.read(chunk),b""): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--allow-root-empty-ext4-lostfound",action="store_true")
    a=ap.parse_args()
    root=pathlib.Path(a.root)
    man=pathlib.Path(a.manifest)
    out=pathlib.Path(a.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    result={
      "root_technical_exclusion":None,
      "schema":"LOUKSNA_R4_PART4_R2_TREE_VERIFY_V9/1.0",
      "root":str(root),
      "manifest":str(man),
      "manifest_sha256":sha256_file(man),
      "status":"HOLD",
      "mismatches":[],
      "counts":{"file":0,"dir":0,"symlink":0,"other":0},
      "regular_file_bytes":0,
      "seen_records":0,
      "started_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    }
    if result["manifest_sha256"]!=EXPECTED_MANIFEST_SHA256:
        result["mismatches"].append({"reason":"MANIFEST_DIGEST_MISMATCH"})
    expected={}
    with gzip.open(man,"rt",encoding="utf-8") as f:
        for line in f:
            r=json.loads(line); expected[r["path"]]=r
    seen=set(); stack=[root]
    while stack:
        d=stack.pop()
        for e in os.scandir(d):
            p=pathlib.Path(e.path); rel=p.relative_to(root).as_posix()
            if rel=="lost+found" and d==root and a.allow_root_empty_ext4_lostfound:
                st_lf=e.stat(follow_symlinks=False)
                try:
                    children=sorted(x.name for x in os.scandir(p))
                except OSError as ex:
                    children=["SCAN_FAILED:"+repr(ex)]
                proof={"path":rel,"owner":st_lf.st_uid,"group":st_lf.st_gid,
                       "mode":oct(stat.S_IMODE(st_lf.st_mode)),
                       "same_device":st_lf.st_dev==root.stat().st_dev,
                       "root_is_mount":os.path.ismount(root),
                       "directory":stat.S_ISDIR(st_lf.st_mode),
                       "not_symlink":not stat.S_ISLNK(st_lf.st_mode),
                       "not_nested_mount":not os.path.ismount(p),
                       "children":children}
                result["root_technical_exclusion"]=proof
                if not (proof["owner"]==0 and proof["group"]==0 and
                        proof["mode"]=="0o700" and proof["same_device"] and
                        proof["root_is_mount"] and proof["directory"] and
                        proof["not_symlink"] and proof["not_nested_mount"] and
                        not proof["children"] and "lost+found" not in expected):
                    result["mismatches"].append({"path":rel,"reason":"INVALID_EXT4_ROOT_LOST_FOUND", "proof":proof})
                continue
            seen.add(rel)
            exp=expected.get(rel)
            if exp is None:
                result["mismatches"].append({"path":rel,"reason":"EXTRA"}); continue
            st=e.stat(follow_symlinks=False)
            typ="file" if stat.S_ISREG(st.st_mode) else "dir" if stat.S_ISDIR(st.st_mode) else "symlink" if stat.S_ISLNK(st.st_mode) else "other"
            result["counts"][typ]+=1
            if typ!=exp.get("type"):
                result["mismatches"].append({"path":rel,"reason":"TYPE","expected":exp.get("type"),"actual":typ}); continue
            if typ=="file":
                result["regular_file_bytes"]+=st.st_size
                if st.st_size!=exp.get("size"):
                    result["mismatches"].append({"path":rel,"reason":"SIZE","expected":exp.get("size"),"actual":st.st_size}); continue
                h=sha256_file(p)
                if h!=exp.get("sha256"):
                    result["mismatches"].append({"path":rel,"reason":"SHA256","expected":exp.get("sha256"),"actual":h})
            elif typ=="dir":
                stack.append(p)
            elif typ=="symlink":
                try:t=os.readlink(p)
                except Exception as ex:
                    result["mismatches"].append({"path":rel,"reason":"READLINK","error":repr(ex)}); continue
                if t!=exp.get("target"):
                    result["mismatches"].append({"path":rel,"reason":"SYMLINK_TARGET","expected":exp.get("target"),"actual":t})
            if len(result["mismatches"])>1000:
                break
        if len(result["mismatches"])>1000:
            break
    missing=sorted(set(expected)-seen)
    if missing:
        result["mismatches"].extend({"path":p,"reason":"MISSING"} for p in missing[:1000])
    result["seen_records"]=len(seen)
    checks={
      "manifest_digest":result["manifest_sha256"]==EXPECTED_MANIFEST_SHA256,
      "mismatch_count_zero":len(result["mismatches"])==0,
      "record_count":len(seen)==EXPECTED_RECORDS,
      "counts":result["counts"]==EXPECTED_COUNTS,
      "regular_file_bytes":result["regular_file_bytes"]==EXPECTED_BYTES,
      "technical_exclusion_strict":not a.allow_root_empty_ext4_lostfound or (result["root_technical_exclusion"] is not None and not any(m.get("reason")=="INVALID_EXT4_ROOT_LOST_FOUND" for m in result["mismatches"]))
    }
    result["checks"]=checks
    result["status"]="PASS" if all(checks.values()) else "HOLD"
    result["mismatch_count"]=len(result["mismatches"])
    result["mismatches"]=result["mismatches"][:100]
    result["finished_at_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    raw=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    out.write_text(raw,encoding="utf-8")
    print(raw)
    return 0 if result["status"]=="PASS" else 3

if __name__=="__main__":
    raise SystemExit(main())
